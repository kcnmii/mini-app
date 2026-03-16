"""Pydantic schemas for the Invoice / Payment domain (Phase 1)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Invoice Items ──

class InvoiceItemCreate(BaseModel):
    catalog_item_id: Optional[int] = None
    name: str
    quantity: float = 1.0
    unit: str = "шт."
    price: float = 0.0
    total: float = 0.0
    code: str = ""


class InvoiceItemRead(InvoiceItemCreate):
    id: int
    invoice_id: int

    model_config = {"from_attributes": True}


# ── Invoice ──

class InvoiceCreate(BaseModel):
    number: str
    date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    client_id: Optional[int] = None
    client_name: str = ""
    client_bin: str = ""
    deal_reference: str = ""
    payment_code: str = ""
    items: List[InvoiceItemCreate] = []
    # render payload is passed through when we need PDF generation
    render_payload: Optional[dict] = None


class InvoiceRead(BaseModel):
    id: int
    number: str
    date: datetime
    due_date: Optional[datetime] = None
    client_id: Optional[int] = None
    client_name: str = ""
    client_bin: str = ""
    deal_reference: str = ""
    payment_code: str = ""
    status: str = "draft"
    total_amount: float = 0.0
    pdf_path: str = ""
    docx_path: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None
    line_items: List[InvoiceItemRead] = []

    model_config = {"from_attributes": True}


class InvoiceStatusUpdate(BaseModel):
    status: str  # sent | paid | overdue | draft


# ── Payment ──

class PaymentCreate(BaseModel):
    amount: Optional[float] = None  # defaults to invoice total
    date: Optional[datetime] = None
    note: str = ""


class PaymentRead(BaseModel):
    id: int
    invoice_id: int
    amount: float
    date: datetime
    source: str = "manual"
    note: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ──

class DashboardSummary(BaseModel):
    awaiting: float = 0.0        # total for sent invoices
    overdue: float = 0.0         # total for overdue invoices
    paid_this_month: float = 0.0 # total payments this month
    invoices_count: int = 0
    overdue_count: int = 0
