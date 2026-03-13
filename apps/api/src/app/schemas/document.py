from pydantic import BaseModel

from app.schemas.render import InvoiceRenderPayload


class DocumentRead(BaseModel):
    id: int
    title: str
    client_name: str
    total_sum: str
    total_sum_in_words: str
    pdf_path: str
    created_at: str


class SaveInvoiceRequest(BaseModel):
    payload: InvoiceRenderPayload
