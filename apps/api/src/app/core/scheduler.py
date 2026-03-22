"""Background scheduler for automated notifications via Telegram.

Runs periodic tasks:
1. Daily overdue check (09:00 UTC+5) — notify users about overdue invoices
2. Weekly digest (Monday 10:00 UTC+5) — summary + remind to upload bank statement
3. Status-change push (event-driven, called from router) — instant notification
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, Invoice, Payment
from app.core.config import settings
from app.modules.telegram_bot.service import TelegramBotClient

logger = logging.getLogger("scheduler")

# Kazakhstan timezone offset (UTC+5)
KZ_OFFSET = timedelta(hours=5)


def _all_user_ids(db: Session) -> list[int]:
    """Get all distinct user_ids that have at least one invoice."""
    rows = db.query(Invoice.user_id).distinct().all()
    return [r[0] for r in rows]


@contextmanager
def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Daily overdue check ─────────────────────────────────────────────────────

async def check_overdue_invoices() -> None:
    """Find invoices that are overdue and notify users via Telegram.
    
    Also auto-marks 'sent' invoices as 'overdue' if due_date has passed.
    """
    logger.info("Running daily overdue check...")
    
    with get_session() as db:
        now = datetime.now(timezone.utc)
        
        # Auto-mark sent invoices as overdue
        updated = (
            db.query(Invoice)
            .filter(
                Invoice.status == "sent",
                Invoice.due_date.isnot(None),
                Invoice.due_date < now,
            )
            .update({"status": "overdue", "updated_at": now}, synchronize_session="fetch")
        )
        if updated:
            db.commit()
            logger.info(f"Auto-marked {updated} invoices as overdue")
        
        # Collect overdue stats per user
        user_ids = _all_user_ids(db)
        
        for user_id in user_ids:
            overdue_invoices = (
                db.query(Invoice)
                .filter(
                    Invoice.user_id == user_id,
                    Invoice.status == "overdue",
                )
                .all()
            )
            
            if not overdue_invoices:
                continue
            
            total_overdue = sum(inv.total_amount for inv in overdue_invoices)
            count = len(overdue_invoices)
            
            # Build message
            lines = [f"⚠️ <b>Просрочено: {count} счёт(ов)</b>\n"]
            lines.append(f"Общая сумма: <b>{total_overdue:,.0f} ₸</b>\n")
            
            for inv in overdue_invoices[:5]:
                days_overdue = (now - inv.due_date).days if inv.due_date else 0
                lines.append(
                    f"• <code>{inv.number}</code> — {inv.client_name or 'Без клиента'} — "
                    f"<b>{inv.total_amount:,.0f} ₸</b> "
                    f"({days_overdue} дн.)"
                )
            
            if count > 5:
                lines.append(f"\n...и ещё {count - 5}")
            
            lines.append(f"\n💡 <i>Напомните клиентам об оплате в приложении.</i>")
            
            bot = TelegramBotClient()
            try:
                await bot.send_message(chat_id=user_id, text="\n".join(lines))
                logger.info(f"Sent overdue notification to user {user_id}: {count} invoices")
            except Exception as e:
                logger.error(f"Failed to send overdue notification to {user_id}: {e}")
            finally:
                await bot.close()


# ─── Weekly digest ────────────────────────────────────────────────────────────

async def send_weekly_digest() -> None:
    """Send weekly financial summary + remind to upload bank statement."""
    logger.info("Running weekly digest...")
    
    with get_session() as db:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        
        user_ids = _all_user_ids(db)
        
        for user_id in user_ids:
            # Stats for the week
            new_invoices_count = (
                db.query(func.count(Invoice.id))
                .filter(Invoice.user_id == user_id, Invoice.created_at >= week_ago)
                .scalar()
            ) or 0
            
            paid_amount = (
                db.query(func.coalesce(func.sum(Payment.amount), 0.0))
                .filter(Payment.user_id == user_id, Payment.created_at >= week_ago)
                .scalar()
            ) or 0
            
            awaiting_amount = (
                db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0))
                .filter(
                    Invoice.user_id == user_id,
                    Invoice.status.in_(["sent", "overdue"]),
                )
                .scalar()
            ) or 0
            
            overdue_count = (
                db.query(func.count(Invoice.id))
                .filter(Invoice.user_id == user_id, Invoice.status == "overdue")
                .scalar()
            ) or 0
            
            # Only send if there's any activity
            if new_invoices_count == 0 and paid_amount == 0 and awaiting_amount == 0:
                continue
            
            lines = [f"📊 <b>Итоги недели</b>\n"]
            
            if new_invoices_count > 0:
                lines.append(f"📝 Выставлено счетов: <b>{new_invoices_count}</b>")
            
            if paid_amount > 0:
                lines.append(f"✅ Получено оплат: <b>{paid_amount:,.0f} ₸</b>")
            
            if awaiting_amount > 0:
                lines.append(f"⏳ Ожидается: <b>{awaiting_amount:,.0f} ₸</b>")
            
            if overdue_count > 0:
                lines.append(f"⚠️ Просрочено: <b>{overdue_count}</b> счёт(ов)")
            
            lines.append(f"\n📥 <i>Загрузите банковскую выписку, чтобы обновить статусы оплат.</i>")
            
            bot = TelegramBotClient()
            try:
                await bot.send_message(chat_id=user_id, text="\n".join(lines))
                logger.info(f"Sent weekly digest to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send weekly digest to {user_id}: {e}")
            finally:
                await bot.close()


# ─── Event-driven notifications ──────────────────────────────────────────────

async def notify_status_change(user_id: int, invoice: Invoice, new_status: str) -> None:
    """Push notification when invoice status changes (called from routers)."""
    status_messages = {
        "sent": (
            f"📤 <b>Счёт отправлен</b>\n\n"
            f"Счет: <code>{invoice.number}</code>\n"
            f"Клиент: {invoice.client_name or 'Без клиента'}\n"
            f"Сумма: <b>{invoice.total_amount:,.0f} ₸</b>"
        ),
        "overdue": (
            f"⚠️ <b>Счёт просрочен!</b>\n\n"
            f"Счет: <code>{invoice.number}</code>\n"
            f"Клиент: {invoice.client_name or 'Без клиента'}\n"
            f"Сумма: <b>{invoice.total_amount:,.0f} ₸</b>\n\n"
            f"💡 <i>Отправьте напоминание клиенту в приложении.</i>"
        ),
    }
    
    msg = status_messages.get(new_status)
    if not msg:
        return  # paid already handled in mark_invoice_paid
    
    bot = TelegramBotClient()
    try:
        await bot.send_message(chat_id=user_id, text=msg)
    except Exception as e:
        logger.error(f"Failed to send status change notification: {e}")
    finally:
        await bot.close()


async def send_payment_reminder(
    user_id: int,
    invoice: Invoice,
    recipient_chat_id: int | None = None,
) -> str:
    """Send a payment reminder for a specific invoice.
    
    If recipient_chat_id is provided, sends directly to the client.
    Otherwise sends to the user themselves (they can forward it).
    
    Returns the reminder text that was sent.
    """
    reminder_text = (
        f"Здравствуйте!\n\n"
        f"Напоминаем об оплате счёта <b>№{invoice.number}</b>\n"
        f"Сумма: <b>{invoice.total_amount:,.0f} ₸</b>\n"
    )
    
    if invoice.due_date:
        due_str = invoice.due_date.strftime("%d.%m.%Y")
        now = datetime.now(timezone.utc)
        if invoice.due_date < now:
            days_overdue = (now - invoice.due_date).days
            reminder_text += f"Срок оплаты: {due_str} (просрочено {days_overdue} дн.)\n"
        else:
            reminder_text += f"Срок оплаты: {due_str}\n"
    
    reminder_text += f"\nБудем признательны за своевременную оплату. 🙏"
    
    target_chat = recipient_chat_id or user_id
    
    bot = TelegramBotClient()
    try:
        await bot.send_message(chat_id=target_chat, text=reminder_text)
    except Exception as e:
        logger.error(f"Failed to send payment reminder: {e}")
        raise
    finally:
        await bot.close()
    
    return reminder_text


# ─── Scheduler loop ──────────────────────────────────────────────────────────

async def _scheduler_loop() -> None:
    """Main scheduler loop running in background.
    
    Uses simple asyncio.sleep-based scheduling:
    - Checks every 60 seconds what tasks need to run
    - Runs overdue check once daily at 09:00 KZ time (04:00 UTC)
    - Runs weekly digest on Mondays at 10:00 KZ time (05:00 UTC)
    """
    last_overdue_check_date = None
    last_weekly_digest_date = None
    
    logger.info("Notification scheduler started")
    
    # Wait 30 seconds on startup for DB to be ready
    await asyncio.sleep(30)
    
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            now_kz = now_utc + KZ_OFFSET
            today = now_kz.date()
            current_hour = now_kz.hour
            weekday = now_kz.weekday()  # 0 = Monday
            
            # Daily overdue check at 09:00 KZ
            if current_hour >= 9 and last_overdue_check_date != today:
                last_overdue_check_date = today
                try:
                    await check_overdue_invoices()
                except Exception as e:
                    logger.error(f"Overdue check failed: {e}")
            
            # Weekly digest on Monday at 10:00 KZ
            if weekday == 0 and current_hour >= 10 and last_weekly_digest_date != today:
                last_weekly_digest_date = today
                try:
                    await send_weekly_digest()
                except Exception as e:
                    logger.error(f"Weekly digest failed: {e}")
            
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        
        # Sleep 60 seconds before next check
        await asyncio.sleep(60)


def start_scheduler() -> None:
    """Start the background scheduler as an asyncio task."""
    loop = asyncio.get_event_loop()
    loop.create_task(_scheduler_loop())
    logger.info("Notification scheduler task created")
