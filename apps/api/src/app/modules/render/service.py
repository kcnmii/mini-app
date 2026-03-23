from __future__ import annotations

from pathlib import Path

import httpx

from app.core.config import settings
from app.core import s3
from app.schemas.render import InvoiceRenderPayload


class RenderService:
    async def render_invoice_docx(self, payload: InvoiceRenderPayload, user_id: int) -> bytes:
        return await self.render_document_docx("invoice-kz", payload.to_template_data(user_id=user_id))

    async def render_document_docx(self, template_key: str, data: dict) -> bytes:
        """Generic DOCX renderer — works for any template key (invoice-kz, act-kz, waybill-kz)."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.docgen_url}/render/docx",
                json={
                    "templateKey": template_key,
                    "templateVersion": "v1",
                    "data": data,
                },
            )
            response.raise_for_status()
            return response.content

    async def convert_docx_to_pdf(self, filename: str, docx_bytes: bytes) -> bytes:
        files = {
            "files": (
                filename,
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        auth = None
        if settings.service_user_gotenberg and settings.service_password_gotenberg:
            auth = (settings.service_user_gotenberg, settings.service_password_gotenberg)

        async with httpx.AsyncClient(timeout=120, auth=auth) as client:
            response = await client.post(
                f"{settings.service_url_gotenberg}/forms/libreoffice/convert",
                files=files,
            )
            response.raise_for_status()
            return response.content

    async def save_file(self, filename: str, content: bytes, user_id: int = 0) -> str:
        s3_key = f"invoices/{user_id}/{filename}"
        mime = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        await s3.upload_file(s3_key, content, content_type=mime)
        return s3_key
