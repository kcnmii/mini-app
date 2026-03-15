from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import re

from app.core.db import get_db, BankAccount, BankTransaction, Invoice, Payment
from app.core.auth import get_current_user_id
from app.schemas.bank import BankAccountSchema, BankStatementImportPayload, ImportResponse, MatchResult, BankTransactionSchema
from app.modules.telegram_bot.service import TelegramBotClient

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
    # Try to find by account_number
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

@router.post("/import", response_model=ImportResponse)
async def import_statements(
    payload: BankStatementImportPayload,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Import statement transactions (already parsed from 1C from frontend) to the DB and try matching them to invoices."""
    
    # 1. Ensure account exists
    acc = db.query(BankAccount).filter(
        BankAccount.user_id == user_id, 
        BankAccount.account_number == payload.account_number
    ).first()

    if not acc:
        acc = BankAccount(
            user_id=user_id,
            account_number=payload.account_number,
            bank_name=payload.bank_name,
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)

    # 2. Iterate transactions
    added_count = 0
    matched_count = 0
    matches = []

    for item in payload.transactions:
        # Deduplication check
        existing_tx = db.query(BankTransaction).filter(
            BankTransaction.user_id == user_id,
            BankTransaction.bank_account_id == acc.id,
            BankTransaction.amount == item.amount,
            BankTransaction.is_income == int(item.is_income),
            BankTransaction.doc_num == item.doc_num,
            # We assume day match + amount + type + doc_num is unique
        ).first()

        if existing_tx:
            continue

        new_tx = BankTransaction(
            user_id=user_id,
            bank_account_id=acc.id,
            date=item.date,
            amount=item.amount,
            sender_name=item.sender_name,
            sender_bin=item.sender_bin,
            description=item.description,
            is_income=int(item.is_income),
            doc_num=item.doc_num,
            is_processed=0,
        )

        db.add(new_tx)
        db.flush()
        added_count += 1

        # Match strategy:
        # Only income can pay an invoice
        if item.is_income:
            # Look for an unpaid invoice where the BIN matches + Amount matches
            candidate_invoice = None
            if item.sender_bin:
                candidate_invoice = db.query(Invoice).filter(
                    Invoice.user_id == user_id,
                    Invoice.status.in_(["draft", "sent", "overdue"]),
                    Invoice.client_bin == item.sender_bin,
                    Invoice.total_amount == float(item.amount)  # phase 6 matching: full payment
                ).first()

            # If no BIN match, look for "счет №NNN" in description regex
            if not candidate_invoice:
                match = re.search(r'(?i)счет[а-я]?\s*(?:(?:на\s+оплату|№|N)\s*)?([A-Za-z0-9-]+)', item.description)
                if match:
                    possible_invoice_num = match.group(1).strip()
                    candidate_invoice = db.query(Invoice).filter(
                        Invoice.user_id == user_id,
                        Invoice.status.in_(["draft", "sent", "overdue"]),
                        Invoice.number == possible_invoice_num,
                        Invoice.total_amount == float(item.amount)
                    ).first()

            if candidate_invoice:
                # Mark as Paid
                candidate_invoice.status = "paid"
                # Link
                new_tx.matched_invoice_id = candidate_invoice.id
                new_tx.is_processed = 1
                
                # Add Payment record
                payment = Payment(
                    user_id=user_id,
                    invoice_id=candidate_invoice.id,
                    amount=item.amount,
                    date=item.date,
                    source="bank_import",
                    bank_transaction_id=new_tx.id,
                    note=f"С выписки 1С (док. {item.doc_num})"
                )
                db.add(payment)
                db.flush()

                matched_count += 1
                matches.append(MatchResult(
                    transaction_id=new_tx.id,
                    matched=True,
                    invoice_id=candidate_invoice.id,
                    invoice_number=candidate_invoice.number,
                    client_name=candidate_invoice.client_name,
                ))

                # Telegram notification
                bot = TelegramBotClient()
                try:
                    msg = (
                        f"✅ <b>Оплата получена!</b>\n\n"
                        f"Счет: <code>{candidate_invoice.number}</code>\n"
                        f"Клиент: <code>{candidate_invoice.client_name}</code>\n"
                        f"Сумма: <b>{item.amount:,.2f} ₸</b>\n\n"
                        f"<i>Автоматически разнесено из банковской выписки.</i>"
                    )
                    await bot.send_message(chat_id=user_id, text=msg)
                except Exception as e:
                    print(f"Failed to send telegram notification: {e}")
                finally:
                    await bot.close()

    db.commit()

    return ImportResponse(
        added_count=added_count,
        matched_count=matched_count,
        matches=matches
    )
