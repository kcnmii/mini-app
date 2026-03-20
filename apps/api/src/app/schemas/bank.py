from pydantic import BaseModel
from typing import List, Optional
import datetime

class BankAccountSchema(BaseModel):
    id: Optional[int] = None
    bank_name: str = ""
    account_number: str = "" # IIC
    bic: str = ""
    currency: str = "KZT"
    is_default: bool = False

    model_config = {"from_attributes": True}

# ── Internal parsing models (not stored in DB) ──

class BankTransactionCreate(BaseModel):
    """In-memory representation of a single parsed transaction from a 1C file."""
    date: datetime.datetime
    amount: float
    sender_name: str = ""
    sender_bin: str = ""
    description: str = ""
    is_income: bool = True
    doc_num: str = ""

class BankStatementImportPayload(BaseModel):
    """Result of parsing a 1C file — stays in memory, never stored."""
    account_number: str
    bank_name: str = ""
    transactions: List[BankTransactionCreate]

# ── API Response models ──

class AutoMatchedInvoice(BaseModel):
    """An invoice that was automatically matched and marked as paid."""
    invoice_id: int
    invoice_number: str
    client_name: str
    amount: float
    sender_name: str = ""
    payment_description: str = ""

class NeedsAttentionItem(BaseModel):
    """An incoming payment from a known client, but no exact invoice match found."""
    sender_name: str
    sender_bin: str
    amount: float
    date: datetime.datetime
    description: str = ""
    doc_num: str = ""
    # Possible invoices from this client that are still unpaid
    candidate_invoices: List["CandidateInvoice"] = []

class CandidateInvoice(BaseModel):
    """A possible invoice that an unmatched payment could belong to."""
    invoice_id: int
    invoice_number: str
    total_amount: float
    date: Optional[datetime.datetime] = None
    client_name: str = ""

class ImportResponse(BaseModel):
    """Response from /upload-1c endpoint."""
    total_incomes: int          # how many incoming payments were in the file
    auto_matched_count: int     # how many were auto-matched to invoices
    ignored_count: int          # how many were from unknown parties (ignored)
    auto_matched: List[AutoMatchedInvoice]
    needs_attention: List[NeedsAttentionItem]

class ManualMatchRequest(BaseModel):
    """Request to manually confirm a match between a payment and an invoice."""
    invoice_id: int
    amount: float
    date: datetime.datetime
    sender_name: str = ""
    doc_num: str = ""
    description: str = ""

class ManualMatchResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    client_name: str
    success: bool
