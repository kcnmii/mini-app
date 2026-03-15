"""Invoice CRUD router — the core financial entity (Phase 1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user_id
from app.core.db import get_db, Invoice, NewInvoiceItem, Payment
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceRead,
    InvoiceStatusUpdate,
    PaymentCreate,
    PaymentRead,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _mark_overdue(db: Session, user_id: int) -> int:
    """Auto-update sent invoices whose due_date has passed to 'overdue'.
    Returns number of rows updated.
    """
    now = datetime.now(timezone.utc)
    count = (
        db.query(Invoice)
        .filter(
            Invoice.user_id == user_id,
            Invoice.status == "sent",
            Invoice.due_date.isnot(None),
            Invoice.due_date < now,
        )
        .update({"status": "overdue", "updated_at": now}, synchronize_session="fetch")
    )
    if count:
        db.commit()
    return count


# ── LIST ──

@router.get("", response_model=list[InvoiceRead])
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status: draft|sent|paid|overdue"),
    client_id: Optional[int] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[InvoiceRead]:
    _mark_overdue(db, user_id)
    q = db.query(Invoice).options(
        joinedload(Invoice.line_items),
    ).filter(Invoice.user_id == user_id)
    if status:
        q = q.filter(Invoice.status == status)
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    invoices = q.order_by(Invoice.id.desc()).limit(200).all()
    return invoices


# ── CREATE ──

@router.post("", response_model=InvoiceRead, status_code=201)
async def create_invoice(
    payload: InvoiceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InvoiceRead:
    # Calculate total from items
    total = sum(it.total or (it.quantity * it.price) for it in payload.items)

    inv = Invoice(
        user_id=user_id,
        number=payload.number,
        date=payload.date or datetime.now(timezone.utc),
        due_date=payload.due_date,
        client_id=payload.client_id,
        client_name=payload.client_name,
        client_bin=payload.client_bin,
        deal_reference=payload.deal_reference,
        status="draft",
        total_amount=total,
    )
    db.add(inv)
    db.flush()

    for it in payload.items:
        item_total = it.total or (it.quantity * it.price)
        line = NewInvoiceItem(
            invoice_id=inv.id,
            catalog_item_id=it.catalog_item_id,
            name=it.name,
            quantity=it.quantity,
            unit=it.unit,
            price=it.price,
            total=item_total,
            code=it.code,
        )
        db.add(line)

    db.commit()
    db.refresh(inv)
    return inv


# ── GET DETAIL ──

@router.get("/next-number")
async def get_next_invoice_number(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    import re
    last = db.query(Invoice).filter(Invoice.user_id == user_id).order_by(Invoice.id.desc()).first()
    if not last:
        return {"next_number": "СФ-001"}
    match = re.search(r"(\d+)", last.number)
    if match:
        padding = len(match.group(1))
        next_num = str(int(match.group(1)) + 1).zfill(padding)
        return {"next_number": f"СФ-{next_num}"}
    return {"next_number": "СФ-001"}


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InvoiceRead:
    inv = (
        db.query(Invoice)
        .options(joinedload(Invoice.line_items))
        .filter(Invoice.id == invoice_id, Invoice.user_id == user_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    return inv


# ── UPDATE STATUS ──

VALID_STATUSES = {"draft", "sent", "paid", "overdue"}

@router.patch("/{invoice_id}/status", response_model=InvoiceRead)
async def update_invoice_status(
    invoice_id: int,
    body: InvoiceStatusUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InvoiceRead:
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {body.status}")

    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    inv.status = body.status
    inv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inv)
    return inv


# ── MARK AS PAID ──

@router.post("/{invoice_id}/pay", response_model=PaymentRead, status_code=201)
async def mark_invoice_paid(
    invoice_id: int,
    body: PaymentCreate = PaymentCreate(),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PaymentRead:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    payment_amount = body.amount if body.amount is not None else inv.total_amount

    payment = Payment(
        user_id=user_id,
        invoice_id=inv.id,
        amount=payment_amount,
        date=body.date or datetime.now(timezone.utc),
        source="manual",
        note=body.note,
    )
    db.add(payment)

    inv.status = "paid"
    inv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payment)
    return payment


# ── DELETE ──

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    db.delete(inv)
    db.commit()
    return {"status": "ok"}
