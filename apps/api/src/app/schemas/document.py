from datetime import datetime
from pydantic import BaseModel

from app.schemas.render import InvoiceRenderPayload


class DocumentRead(BaseModel):
    id: int
    title: str
    client_name: str
    total_sum: str
    total_amount: float = 0.0
    total_sum_in_words: str
    pdf_path: str
    docx_path: str = ""
    created_at: datetime
    
    # EDO Fields
    doc_type: str = "invoice"
    edo_status: str = "draft"
    contract_id: int | None = None
    share_uuid: str | None = None

    model_config = {"from_attributes": True}


class DocumentStats(BaseModel):
    count: int
    total_sum: float
    client_count: int


class SaveInvoiceRequest(BaseModel):
    payload: InvoiceRenderPayload
