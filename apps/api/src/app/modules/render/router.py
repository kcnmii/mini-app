from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse, Response
import httpx

from app.core.cors import cors_preflight_response
from app.schemas.render import InvoiceRenderPayload
from app.modules.render.service import RenderService

router = APIRouter(prefix="/render", tags=["render"])
service = RenderService()


def _safe_filename(prefix: str, value: str, extension: str) -> str:
    normalized = "".join(char if char.isascii() and char.isalnum() else "-" for char in value)
    normalized = normalized.strip("-") or "document"
    return f"{prefix}-{normalized}.{extension}"


def _sample_invoice_payload() -> InvoiceRenderPayload:
    return InvoiceRenderPayload.model_validate(
        {
            "INVOICE_NUMBER": "СФ-001",
            "INVOICE_DATE": "10.03.2026",
            "CONTRACT": "Договор без номера",
            "SUPPLIER_NAME": "",
            "SUPPLIER_IIN": "",
            "SUPPLIER_ADDRESS": "",
            "COMPANY_NAME": "",
            "COMPANY_IIN": "",
            "COMPANY_IIC": "",
            "COMPANY_BIC": "",
            "COMPANY_KBE": "19",
            "BENEFICIARY_BANK": "",
            "PAYMENT_CODE": "710",
            "CLIENT_NAME": "",
            "CLIENT_IIN": "",
            "CLIENT_ADDRESS": "",
            "EXECUTOR_NAME": "",
            "POSITION": "",
            "VAT": "Без НДС",
            "ITEMS_TOTAL_LINE": "0",
            "TOTAL_SUM": "0",
            "TOTAL_SUM_IN_WORDS": "Ноль тенге 00 тиын",
            "items": [
                {
                    "number": 1,
                    "name": "Услуга разработки",
                    "quantity": "1",
                    "unit": "усл.",
                    "price": "50 000",
                    "total": "50 000",
                    "code": "DEV-001",
                }
            ],
        }
    )


@router.get("/invoice/sample", response_model=InvoiceRenderPayload)
async def sample_invoice_payload() -> InvoiceRenderPayload:
    return _sample_invoice_payload()


@router.post("/invoice/docx")
async def render_invoice_docx(
    payload: InvoiceRenderPayload | None = Body(default=None),
) -> Response:
    payload = payload or _sample_invoice_payload()
    try:
        docx_bytes = await service.render_invoice_docx(payload, user_id=0)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"docgen_error: {exc}") from exc

    filename = _safe_filename("invoice", payload.invoice_number, "docx")
    service.persist_debug_output(filename, docx_bytes)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.options("/invoice/docx")
async def render_invoice_docx_options() -> Response:
    return cors_preflight_response()


@router.post("/invoice/pdf")
async def render_invoice_pdf(
    payload: InvoiceRenderPayload | None = Body(default=None),
) -> Response:
    payload = payload or _sample_invoice_payload()
    filename = _safe_filename("invoice", payload.invoice_number, "docx")

    try:
        docx_bytes = await service.render_invoice_docx(payload, user_id=0)
        pdf_bytes = await service.convert_docx_to_pdf(filename, docx_bytes)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"render_pipeline_error: {exc}") from exc

    service.persist_debug_output(filename, docx_bytes)
    pdf_name = filename.replace(".docx", ".pdf")
    pdf_path = service.persist_debug_output(pdf_name, pdf_bytes)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{pdf_name}"',
            "X-Debug-Pdf-Path": pdf_path,
        },
    )


@router.options("/invoice/pdf")
async def render_invoice_pdf_options() -> Response:
    return cors_preflight_response()


@router.post("/invoice/debug")
async def render_invoice_debug(
    payload: InvoiceRenderPayload | None = Body(default=None),
) -> JSONResponse:
    payload = payload or _sample_invoice_payload()
    filename = _safe_filename("invoice", payload.invoice_number, "docx")

    try:
        docx_bytes = await service.render_invoice_docx(payload, user_id=0)
        pdf_bytes = await service.convert_docx_to_pdf(filename, docx_bytes)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"render_pipeline_error: {exc}") from exc

    docx_path = service.persist_debug_output(filename, docx_bytes)
    pdf_path = service.persist_debug_output(filename.replace(".docx", ".pdf"), pdf_bytes)
    return JSONResponse(
        {
            "template_key": "invoice-kz",
            "template_version": "v1",
            "docx_path": docx_path,
            "pdf_path": pdf_path,
        }
    )


@router.options("/invoice/debug")
async def render_invoice_debug_options() -> Response:
    return cors_preflight_response()
