"""Dashboard summary — financial overview (Phase 1)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.db import get_db, Invoice, Payment
from app.schemas.invoice import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    # Auto-mark overdue first
    now = datetime.now(timezone.utc)
    db.query(Invoice).filter(
        Invoice.user_id == user_id,
        Invoice.status == "sent",
        Invoice.due_date.isnot(None),
        Invoice.due_date < now,
    ).update({"status": "overdue", "updated_at": now}, synchronize_session="fetch")
    db.commit()

    # Awaiting = sent + overdue totals
    awaiting = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0))
        .filter(Invoice.user_id == user_id, Invoice.status.in_(["sent", "overdue"]))
        .scalar()
    )

    # Overdue only
    overdue = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0))
        .filter(Invoice.user_id == user_id, Invoice.status == "overdue")
        .scalar()
    )

    overdue_count = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.user_id == user_id, Invoice.status == "overdue")
        .scalar()
    )

    # Paid this month — sum of payments created this calendar month
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid_this_month = (
        db.query(func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(Payment.user_id == user_id, Payment.created_at >= first_of_month)
        .scalar()
    )

    # Total invoices count
    invoices_count = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.user_id == user_id)
        .scalar()
    )

    return DashboardSummary(
        awaiting=float(awaiting),
        overdue=float(overdue),
        paid_this_month=float(paid_this_month),
        invoices_count=invoices_count,
        overdue_count=overdue_count,
    )
