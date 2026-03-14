from fastapi import APIRouter, HTTPException, Response, Depends
import httpx

from app.core.cors import cors_preflight_response
from app.core.auth import get_current_user_id
from app.modules.render.router import _sample_invoice_payload
from app.modules.render.service import RenderService
from app.modules.telegram_bot.service import TelegramBotClient
from app.schemas.telegram import TelegramSendInvoiceRequest, TelegramSendInvoiceResponse

router = APIRouter(prefix="/telegram", tags=["telegram"])
render_service = RenderService()


@router.post("/send-invoice", response_model=TelegramSendInvoiceResponse)
async def send_invoice_to_telegram(
    payload: TelegramSendInvoiceRequest,
    user_id: int = Depends(get_current_user_id),
) -> TelegramSendInvoiceResponse:
    invoice_payload = payload.payload or _sample_invoice_payload()
    filename = f"invoice-{''.join(char if char.isascii() and char.isalnum() else '-' for char in invoice_payload.invoice_number).strip('-') or 'document'}.pdf"

    try:
        docx_bytes = await render_service.render_invoice_docx(invoice_payload, user_id)
        pdf_bytes = await render_service.convert_docx_to_pdf(
            filename.replace(".pdf", ".docx"),
            docx_bytes,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"render_pipeline_error: {exc}") from exc

    bot = TelegramBotClient()
    try:
        filename_prefix = filename.replace(".pdf", "")
        message_id = await bot.send_invoice_documents(
            chat_id=payload.chat_id,
            filename_prefix=filename_prefix,
            pdf_bytes=pdf_bytes,
            docx_bytes=docx_bytes,
            caption=payload.caption,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"telegram_send_error: {exc}") from exc
    finally:
        await bot.close()

    return TelegramSendInvoiceResponse(
        ok=True,
        chat_id=payload.chat_id,
        filename=filename,
        message_id=message_id,
    )


@router.options("/send-invoice")
async def send_invoice_to_telegram_options() -> Response:
    return cors_preflight_response()
