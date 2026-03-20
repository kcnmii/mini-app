from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List
import re

from app.core.db import get_db, BankAccount, Invoice, Payment, Client
from app.core.auth import get_current_user_id
from app.schemas.bank import (
    BankAccountSchema, ImportResponse, AutoMatchedInvoice, 
    NeedsAttentionItem, CandidateInvoice, ManualMatchRequest, ManualMatchResponse
)
from app.modules.telegram_bot.service import TelegramBotClient
from app.core.parsers.parser1c import parse_1c_statement, ParseError

router = APIRouter(prefix="/banks", tags=["banks"])

@router.get("/accounts", response_model=List[BankAccountSchema])
async def list_accounts(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List bank accounts for user"""
    return db.query(BankAccount).filter(BankAccount.user_id == user_id).order_by(BankAccount.id).all()

@router.post("/accounts", response_model=BankAccountSchema)
async def create_account(
    payload: BankAccountSchema,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create or update bank account via payload matching"""
    acc = db.query(BankAccount).filter(
        BankAccount.user_id == user_id, 
        BankAccount.account_number == payload.account_number
    ).first()

    if not acc:
        acc = BankAccount(
            user_id=user_id,
            account_number=payload.account_number,
            bank_name=payload.bank_name,
            currency=payload.currency,
        )
        db.add(acc)
    else:
        acc.bank_name = payload.bank_name or acc.bank_name

    db.commit()
    db.refresh(acc)
    return acc


@router.post("/upload-1c", response_model=ImportResponse)
async def upload_1c_statement(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Upload a 1C bank statement file.
    
    Logic:
    1. Parse file in memory (nothing stored yet)
    2. Keep only incoming payments (is_income=True), discard expenses
    3. For each income:
       a) Try auto-match: BIN+Amount or invoice number in description → mark invoice as paid
       b) If BIN is known (exists in clients) but no exact match → "needs_attention"
       c) If BIN is unknown → ignore completely
    4. Nothing from the raw statement is stored in DB. Only Payment records are created for matched invoices.
    """
    # ── Parse file ──
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text_content = content.decode("windows-1251")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Неверная кодировка файла. Поддерживается UTF-8 и Windows-1251.")

    try:
        payload = parse_1c_statement(text_content)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── Ensure bank account exists (auto-create from statement header) ──
    acc = db.query(BankAccount).filter(
        BankAccount.user_id == user_id,
        BankAccount.account_number == payload.account_number
    ).first()

    if not acc:
        existing_count = db.query(BankAccount).filter(BankAccount.user_id == user_id).count()
        acc = BankAccount(
            user_id=user_id,
            account_number=payload.account_number,
            bank_name=payload.bank_name,
            is_default=1 if existing_count == 0 else 0
        )
        db.add(acc)
        db.flush()

    # ── Pre-load user's clients for BIN lookups ──
    user_clients = db.query(Client).filter(Client.user_id == user_id, Client.bin_iin != "").all()
    known_bins = {c.bin_iin: c for c in user_clients}

    # ── Pre-load unpaid invoices ──
    unpaid_invoices = db.query(Invoice).filter(
        Invoice.user_id == user_id,
        Invoice.status.in_(["draft", "sent", "overdue"])
    ).all()

    # Build lookup structures
    # bin → list of invoices (via client_bin or client.bin_iin)
    invoices_by_bin: dict[str, list] = {}
    for inv in unpaid_invoices:
        bins_for_inv = set()
        if inv.client_bin:
            bins_for_inv.add(inv.client_bin)
        if inv.client_id:
            client = next((c for c in user_clients if c.id == inv.client_id), None)
            if client and client.bin_iin:
                bins_for_inv.add(client.bin_iin)
        for b in bins_for_inv:
            invoices_by_bin.setdefault(b, []).append(inv)

    # ── Process only incomes ──
    incomes = [tx for tx in payload.transactions if tx.is_income]
    
    auto_matched: list[AutoMatchedInvoice] = []
    needs_attention: list[NeedsAttentionItem] = []
    ignored_count = 0
    already_matched_invoice_ids: set[int] = set()  # prevent double-matching

    for tx in incomes:
        # ── Strategy 1: Exact match by BIN + Amount ──
        matched_invoice = None
        
        if tx.sender_bin and tx.sender_bin in invoices_by_bin:
            candidates = invoices_by_bin[tx.sender_bin]
            for inv in candidates:
                if inv.id not in already_matched_invoice_ids and abs(inv.total_amount - tx.amount) < 0.01:
                    matched_invoice = inv
                    break

        # ── Strategy 2: Invoice number in payment description ──
        if not matched_invoice:
            m = re.search(r'(?i)(?:счет[а-яё]*|сч\.?)\s*(?:на\s+оплату\s*)?(?:№|N|#)?\s*([A-Za-z0-9/_-]+)', tx.description)
            if m:
                possible_num = m.group(1).strip()
                for inv in unpaid_invoices:
                    if inv.id not in already_matched_invoice_ids and inv.number == possible_num and abs(inv.total_amount - tx.amount) < 0.01:
                        matched_invoice = inv
                        break

        if matched_invoice:
            # ── Auto-match: mark invoice as paid, create Payment ──
            matched_invoice.status = "paid"
            already_matched_invoice_ids.add(matched_invoice.id)

            payment = Payment(
                user_id=user_id,
                invoice_id=matched_invoice.id,
                amount=tx.amount,
                date=tx.date,
                source="bank_import",
                note=f"Из выписки 1С (док. {tx.doc_num})"
            )
            db.add(payment)

            auto_matched.append(AutoMatchedInvoice(
                invoice_id=matched_invoice.id,
                invoice_number=matched_invoice.number,
                client_name=matched_invoice.client_name or "",
                amount=tx.amount,
                sender_name=tx.sender_name,
                payment_description=tx.description
            ))

        elif tx.sender_bin and tx.sender_bin in known_bins:
            # ── Known client, but no exact match → needs attention ──
            # Find their unpaid invoices for manual selection
            client_unpaid = [
                inv for inv in unpaid_invoices
                if inv.id not in already_matched_invoice_ids and (
                    inv.client_bin == tx.sender_bin or
                    (inv.client_id and any(c.id == inv.client_id and c.bin_iin == tx.sender_bin for c in user_clients))
                )
            ]

            candidate_list = [
                CandidateInvoice(
                    invoice_id=inv.id,
                    invoice_number=inv.number,
                    total_amount=inv.total_amount,
                    date=inv.date,
                    client_name=inv.client_name or ""
                )
                for inv in client_unpaid
            ]

            needs_attention.append(NeedsAttentionItem(
                sender_name=tx.sender_name,
                sender_bin=tx.sender_bin,
                amount=tx.amount,
                date=tx.date,
                description=tx.description,
                doc_num=tx.doc_num,
                candidate_invoices=candidate_list
            ))
        else:
            # ── Unknown BIN → ignore completely, nothing stored ──
            ignored_count += 1

    db.commit()

    # ── Send Telegram notification for auto-matched invoices ──
    if auto_matched:
        bot = TelegramBotClient()
        try:
            lines = [f"✅ <b>Выписка загружена!</b>\n"]
            lines.append(f"Автоматически оплачено: <b>{len(auto_matched)}</b> счёт(ов)\n")
            for am in auto_matched[:10]:  # limit to 10 in notification
                lines.append(f"• <code>{am.invoice_number}</code> — {am.client_name} — <b>{am.amount:,.0f} ₸</b>")
            if len(auto_matched) > 10:
                lines.append(f"\n...и ещё {len(auto_matched) - 10}")
            await bot.send_message(chat_id=user_id, text="\n".join(lines))
        except Exception as e:
            print(f"Failed to send telegram notification: {e}")
        finally:
            await bot.close()

    return ImportResponse(
        total_incomes=len(incomes),
        auto_matched_count=len(auto_matched),
        ignored_count=ignored_count,
        auto_matched=auto_matched,
        needs_attention=needs_attention
    )


@router.post("/manual-match", response_model=ManualMatchResponse)
async def manual_match(
    payload: ManualMatchRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Manually confirm a match between a bank payment and an invoice.
    Called from the "Needs Attention" UI when user selects an invoice for an unmatched payment.
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == payload.invoice_id,
        Invoice.user_id == user_id,
        Invoice.status.in_(["draft", "sent", "overdue"])
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Счёт не найден или уже оплачен.")

    # Mark as paid
    invoice.status = "paid"

    payment = Payment(
        user_id=user_id,
        invoice_id=invoice.id,
        amount=payload.amount,
        date=payload.date,
        source="bank_import",
        note=f"Ручное сопоставление из выписки 1С (док. {payload.doc_num})"
    )
    db.add(payment)
    db.commit()

    return ManualMatchResponse(
        invoice_id=invoice.id,
        invoice_number=invoice.number,
        client_name=invoice.client_name or "",
        success=True
    )
