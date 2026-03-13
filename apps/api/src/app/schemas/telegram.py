from pydantic import BaseModel, Field

from app.schemas.render import InvoiceRenderPayload


class TelegramSendInvoiceRequest(BaseModel):
    chat_id: int = Field(description="Telegram chat id or user id")
    caption: str | None = "Счет на оплату"
    payload: InvoiceRenderPayload | None = None


class TelegramSendInvoiceResponse(BaseModel):
    ok: bool
    chat_id: int
    filename: str
    message_id: int | None = None
