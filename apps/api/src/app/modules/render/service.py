from __future__ import annotations

from pathlib import Path

import httpx

from app.core.config import settings
from app.schemas.render import InvoiceRenderPayload


class RenderService:
    async def render_invoice_docx(self, payload: InvoiceRenderPayload) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.docgen_url}/render/docx",
                json={
                    "templateKey": "invoice-kz",
                    "templateVersion": "v1",
                    "data": payload.to_template_data(),
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

    def persist_debug_output(self, filename: str, content: bytes) -> str:
        output_dir = Path("tmp/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_bytes(content)
        return str(output_path.resolve())
