"""
EDO Notification Service — Telegram notifications for document exchange events.

Handles:
  - Incoming document notification (receiver is a registered user)
  - Counterparty signed notification (sender gets notified)
  - Document rejected notification
  - Incoming invoice notification (from guest)
"""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.core.db import Document, SupplierProfile, Invoice
from app.modules.telegram_bot.service import TelegramBotClient

logger = logging.getLogger(__name__)


def _get_profile(db: Session, user_id: int) -> SupplierProfile | None:
    return db.query(SupplierProfile).filter(SupplierProfile.user_id == user_id).first()


async def notify_incoming_document(db: Session, document: Document) -> bool:
    """
    Notify the receiver via Telegram if they are a registered user.
    Called after sender signs + shares, OR after share is created with a matching receiver.
    Returns True if notification was sent.
    """
    receiver_bin = (document.receiver_bin or "").strip()
    if not receiver_bin:
        # Try fallback from payload_json
        if document.payload_json:
            try:
                import json
                payload = json.loads(document.payload_json)
                receiver_bin = str(payload.get("CLIENT_IIN") or "").strip()
            except Exception:
                pass
    if not receiver_bin:
        return False

    # Find all receivers by IIN/BIN
    receiver_profiles = db.query(SupplierProfile).filter(
        SupplierProfile.company_iin == receiver_bin
    ).all()

    if not receiver_profiles:
        return False  # Not a registered user

    # Automatically map the document to the first receiver's user_id 
    # to maintain history if their IIN changes.
    first_user_id = receiver_profiles[0].user_id
    if document.receiver_user_id != first_user_id:
        document.receiver_user_id = first_user_id
        db.commit()

    # Get sender info
    sender_profile = _get_profile(db, document.user_id)
    sender_name = (sender_profile.company_name if sender_profile else "") or "Неизвестный"

    # Doc type label
    doc_type_labels = {"act": "Акт выполненных работ", "waybill": "Накладная", "invoice": "Счёт на оплату"}
    doc_label = doc_type_labels.get(document.doc_type or "", document.title or "Документ")

    msg = (
        f"📩 <b>Входящий документ</b>\n\n"
        f"От: <b>{sender_name}</b>\n"
        f"Документ: <code>{document.title or doc_label}</code>\n"
        f"Сумма: <b>{document.total_sum or '—'} ₸</b>\n\n"
        f"Откройте приложение для просмотра и подписания."
    )

    bot = TelegramBotClient()
    success = False
    try:
        for profile in receiver_profiles:
            if profile.user_id == document.user_id:
                continue
            if not profile.notifications_enabled:
                continue
            try:
                await bot.send_message(chat_id=profile.user_id, text=msg)
                logger.info("Sent incoming document notification to user %d for doc %d", profile.user_id, document.id)
                success = True
            except Exception as e:
                logger.error("Failed to send incoming document notification to %d: %s", profile.user_id, e)
    finally:
        await bot.close()
    
    return success


async def notify_document_countersigned(db: Session, document: Document, signer_name: str) -> bool:
    """
    Notify document OWNER that the counterparty has signed.
    Called after receiver's signature is saved (both guest page and registered user).
    """
    owner_id = document.user_id
    profile = _get_profile(db, owner_id)

    if profile and not profile.notifications_enabled:
        return False

    msg = (
        f"✅ <b>Документ подписан контрагентом!</b>\n\n"
        f"Документ: <code>{document.title}</code>\n"
        f"Подписант: <b>{signer_name}</b>\n"
        f"Сумма: <b>{document.total_sum or '—'} ₸</b>\n\n"
        f"Документ подписан обеими сторонами. PDF со штампом ЭЦП обновлён.\n"
        f"Вы можете скачать исходники для внешней проверки ниже."
    )

    bot = TelegramBotClient()
    try:
        # Pass document_id to show the ZIP download button
        await bot.send_message(
            chat_id=owner_id, 
            text=msg, 
            document_id=document.id if document.edo_status == "signed_both" else None
        )
        logger.info("Sent countersigned notification to user %d for doc %d", owner_id, document.id)
        return True
    except Exception as e:
        logger.error("Failed to send countersigned notification to %d: %s", owner_id, e)
        return False
    finally:
        await bot.close()


async def notify_document_rejected(db: Session, document: Document, comment: str) -> bool:
    """
    Notify document OWNER that the counterparty has rejected the document.
    """
    owner_id = document.user_id
    profile = _get_profile(db, owner_id)

    if profile and not profile.notifications_enabled:
        return False

    msg = (
        f"❌ <b>Документ отклонён контрагентом</b>\n\n"
        f"Документ: <code>{document.title}</code>\n"
        f"Сумма: <b>{document.total_sum or '—'} ₸</b>\n"
        f"Причина: {comment or 'Не указана'}\n\n"
        f"Вы можете создать новый документ в приложении."
    )

    bot = TelegramBotClient()
    try:
        await bot.send_message(chat_id=owner_id, text=msg)
        logger.info("Sent rejection notification to user %d for doc %d", owner_id, document.id)
        return True
    except Exception as e:
        logger.error("Failed to send rejection notification to %d: %s", owner_id, e)
        return False
    finally:
        await bot.close()


async def notify_incoming_invoice(db: Session, target_user_id: int, invoice: Invoice, sender_name: str) -> bool:
    """
    Notify a registered user about an incoming invoice (from guest or another user).
    """
    profile = _get_profile(db, target_user_id)
    if profile and not profile.notifications_enabled:
        return False

    msg = (
        f"📩 <b>Входящий счёт</b>\n\n"
        f"От: <b>{sender_name}</b>\n"
        f"Счёт: <code>{invoice.number}</code>\n"
        f"Сумма: <b>{invoice.total_amount:,.0f} ₸</b>\n\n"
        f"Откройте приложение для просмотра."
    )

    bot = TelegramBotClient()
    try:
        await bot.send_message(chat_id=target_user_id, text=msg)
        logger.info("Sent incoming invoice notification to user %d", target_user_id)
        return True
    except Exception as e:
        logger.error("Failed to send incoming invoice notification to %d: %s", target_user_id, e)
        return False
    finally:
        await bot.close()
