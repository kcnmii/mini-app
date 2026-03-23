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
    from_date: str | None = None,
    to_date: str | None = None,
    all_time: bool = False,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    # Auto-mark overdue first
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(Invoice).filter(
        Invoice.user_id == user_id,
        Invoice.status == "sent",
        Invoice.due_date.isnot(None),
        Invoice.due_date < now,
    ).update({"status": "overdue", "updated_at": now}, synchronize_session="fetch")
    db.commit()

    # Parse dates if provided
    start_dt = None
    end_dt = None
    if from_date:
        try:
            start_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    if to_date:
        try:
            end_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Awaiting = sent only (not overdue anymore)
    awaiting_query = db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0)).filter(
        Invoice.user_id == user_id, Invoice.status == "sent"
    )
    if start_dt:
        awaiting_query = awaiting_query.filter(Invoice.due_date >= start_dt)
    if end_dt:
        awaiting_query = awaiting_query.filter(Invoice.due_date <= end_dt)
    
    awaiting = awaiting_query.scalar()

    # Overdue only
    overdue_query = db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0)).filter(
        Invoice.user_id == user_id, Invoice.status == "overdue"
    )
    if start_dt:
        overdue_query = overdue_query.filter(Invoice.due_date >= start_dt)
    if end_dt:
        overdue_query = overdue_query.filter(Invoice.due_date <= end_dt)
    
    overdue = overdue_query.scalar()

    # Overdue count
    overdue_count_query = db.query(func.count(Invoice.id)).filter(
        Invoice.user_id == user_id, Invoice.status == "overdue"
    )
    if start_dt:
        overdue_count_query = overdue_count_query.filter(Invoice.due_date >= start_dt)
    if end_dt:
        overdue_count_query = overdue_count_query.filter(Invoice.due_date <= end_dt)
    
    overdue_count = overdue_count_query.scalar()

    # Received (Paid) calculation
    paid_query = db.query(func.coalesce(func.sum(Payment.amount), 0.0)).filter(
        Payment.user_id == user_id
    )
    
    if start_dt:
        paid_query = paid_query.filter(Payment.created_at >= start_dt)
    elif not to_date and not all_time:
        # Default to current month if no filter at all
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        paid_query = paid_query.filter(Payment.created_at >= first_of_month)
        
    if end_dt:
        paid_query = paid_query.filter(Payment.created_at <= end_dt)
        
    paid_received = paid_query.scalar()

    # Total invoices count
    invoices_count = db.query(func.count(Invoice.id)).filter(Invoice.user_id == user_id).scalar()

    return DashboardSummary(
        awaiting=float(awaiting),
        overdue=float(overdue),
        paid_this_month=float(paid_received),
        invoices_count=invoices_count,
        overdue_count=overdue_count,
    )
