from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import httpx
import os

from app.core.db import get_db
from app.modules.render.service import RenderService
from app.schemas.document import DocumentRead, SaveInvoiceRequest

router = APIRouter(prefix="/documents", tags=["documents"])
render_service = RenderService()


@router.get("/recent", response_model=list[DocumentRead])
async def list_recent_documents() -> list[DocumentRead]:
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, title, client_name, total_sum, total_sum_in_words, pdf_path, created_at
            FROM documents
            ORDER BY id DESC
            LIMIT 50
            """
        ).fetchall()
    return [DocumentRead.model_validate(dict(row)) for row in rows]


@router.get("/{document_id}")
async def get_document(document_id: int):
    with get_db() as connection:
        row = connection.execute(
            """
            SELECT id, title, client_name, total_sum, total_sum_in_words, pdf_path, payload_json, created_at
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Документ не найден")

        doc_data = dict(row)
        if not doc_data.get("payload_json"):
            # Try to reconstruct basic payload from items table if json is missing
            items_rows = connection.execute(
                "SELECT name, quantity, unit, price, total, code FROM document_items WHERE document_id = ?",
                (document_id,)
            ).fetchall()
            doc_data["reconstructed_items"] = [dict(r) for r in items_rows]

    return doc_data


@router.get("/{document_id}/pdf")
async def get_document_pdf(document_id: int):
    with get_db() as connection:
        row = connection.execute("SELECT pdf_path FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not row or not row["pdf_path"] or not os.path.exists(row["pdf_path"]):
        raise HTTPException(status_code=404, detail="PDF не найден")
    pdf_path = row["pdf_path"]
    filename = os.path.basename(pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


@router.post("/invoice", response_model=DocumentRead)
async def save_invoice_document(payload: SaveInvoiceRequest) -> DocumentRead:
    invoice = payload.payload
    filename = f"invoice-{''.join(char if char.isascii() and char.isalnum() else '-' for char in invoice.invoice_number).strip('-') or 'document'}.docx"

    try:
        docx_bytes = await render_service.render_invoice_docx(invoice)
        pdf_bytes = await render_service.convert_docx_to_pdf(filename, docx_bytes)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"render_pipeline_error: {exc}") from exc

    pdf_path = render_service.persist_debug_output(filename.replace(".docx", ".pdf"), pdf_bytes)

    with get_db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO documents (title, client_name, total_sum, total_sum_in_words, pdf_path, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"Счет № {invoice.invoice_number}",
                invoice.client_name,
                invoice.total_sum,
                invoice.total_sum_in_words,
                pdf_path,
                invoice.model_dump_json(by_alias=True),
            ),
        )
        document_id = cursor.lastrowid

        for item in invoice.items:
            connection.execute(
                """
                INSERT INTO document_items (document_id, name, quantity, unit, price, total, code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    item.name,
                    item.quantity,
                    item.unit,
                    item.price,
                    item.total,
                    item.code,
                ),
            )

        row = connection.execute(
            """
            SELECT id, title, client_name, total_sum, total_sum_in_words, pdf_path, payload_json, created_at
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    return DocumentRead.model_validate(dict(row))
@router.delete("/{document_id}")
async def delete_document(document_id: int):
    with get_db() as connection:
        # Delete items first if no cascade
        connection.execute("DELETE FROM document_items WHERE document_id = ?", (document_id,))
        cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Документ не найден")
    return {"status": "ok"}
