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

class BankTransactionBase(BaseModel):
    date: datetime.datetime
    amount: float
    sender_name: str = ""
    sender_bin: str = ""
    description: str = ""
    is_income: bool = True
    doc_num: str = ""

class BankTransactionCreate(BankTransactionBase):
    pass

class BankTransactionSchema(BankTransactionBase):
    id: int
    bank_account_id: int
    matched_invoice_id: Optional[int] = None
    is_processed: bool = False

    model_config = {"from_attributes": True}

class BankStatementImportPayload(BaseModel):
    account_number: str
    bank_name: str = ""
    transactions: List[BankTransactionCreate]

class MatchResult(BaseModel):
    transaction_id: int
    matched: bool
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    client_name: Optional[str] = None

class ImportResponse(BaseModel):
    added_count: int
    matched_count: int
    matches: List[MatchResult]
