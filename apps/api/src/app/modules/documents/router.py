from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import httpx
import os
import re

from app.core.db import get_db, Document, DocumentItem, Client
from app.core.auth import get_current_user_id
from app.modules.render.service import RenderService
from app.schemas.document import DocumentRead, SaveInvoiceRequest, DocumentStats

router = APIRouter(prefix="/documents", tags=["documents"])
render_service = RenderService()


@router.get("/recent", response_model=list[DocumentRead])
async def list_recent_documents(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    docs = db.query(Document).filter(Document.user_id == user_id).order_by(Document.id.desc()).limit(50).all()
    return docs


@router.get("/stats", response_model=DocumentStats)
async def get_document_stats(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DocumentStats:
    count = db.query(Document).filter(Document.user_id == user_id).count()
    total_sum = db.query(func.sum(Document.total_amount)).filter(Document.user_id == user_id).scalar() or 0.0
    client_count = db.query(Client).filter(Client.user_id == user_id).count()
    return DocumentStats(count=count, total_sum=total_sum, client_count=client_count)


@router.get("/next-number")
async def get_next_invoice_number(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    last_doc = db.query(Document).filter(Document.user_id == user_id).order_by(Document.id.desc()).first()
    if not last_doc:
        return {"next_number": "СФ-001"}
    
    # Try to extract number from title "Счет № 001" or "invoice-001"
    match = re.search(r'(\d+)', last_doc.title)
    if match:
        num = int(match.group(1))
        # Preserving padding if possible
        padding = len(match.group(1))
        next_num = str(num + 1).zfill(padding)
        # Prefix "СФ-" is common in KZ
        return {"next_number": f"СФ-{next_num}"}
    
    return {"next_number": "СФ-001"}


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    doc_data = {
        "id": doc.id,
        "title": doc.title,
        "client_name": doc.client_name,
        "total_sum": doc.total_sum,
        "total_sum_in_words": doc.total_sum_in_words,
        "pdf_path": doc.pdf_path,
        "payload_json": doc.payload_json,
        "doc_type": doc.doc_type,
        "edo_status": doc.edo_status,
        "contract_id": doc.contract_id,
        "share_uuid": doc.share_uuid,
        "created_at": doc.created_at,
    }

    if not doc_data.get("payload_json"):
        items = db.query(DocumentItem).filter(DocumentItem.document_id == document_id).all()
        doc_data["reconstructed_items"] = [
            {
                "name": it.name,
                "quantity": it.quantity,
                "unit": it.unit,
                "price": it.price,
                "total": it.total,
                "code": it.code,
            }
            for it in items
        ]

    return doc_data


@router.get("/{document_id}/pdf")
async def get_document_pdf(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response
    from app.core import s3

    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # If file exists on S3 — return immediately
    if doc.pdf_path:
        pdf_bytes = await s3.download_file(doc.pdf_path)
        if pdf_bytes:
            filename = os.path.basename(doc.pdf_path)
            return Response(pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    # Auto-regenerate from payload_json if available
    if not doc.payload_json:
        raise HTTPException(status_code=404, detail="PDF не найден и нет данных для генерации")

    import json
    from app.schemas.render import InvoiceRenderPayload

    try:
        payload_data = json.loads(doc.payload_json)
        render_payload = InvoiceRenderPayload(**payload_data)

        safe_title = ''.join(c if c.isascii() and c.isalnum() else '-' for c in (doc.title or 'doc')).strip('-') or 'document'
        fname = f"{safe_title}.docx"

        docx_bytes = await render_service.render_invoice_docx(render_payload, user_id)
        pdf_bytes = await render_service.convert_docx_to_pdf(fname, docx_bytes)

        pdf_path = await render_service.save_file(fname.replace(".docx", ".pdf"), pdf_bytes, user_id=user_id)
        docx_path = await render_service.save_file(fname, docx_bytes, user_id=user_id)

        # Update record with new persistent paths
        doc.pdf_path = pdf_path
        doc.docx_path = docx_path
        db.commit()

        return Response(pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{os.path.basename(pdf_path)}"'})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка генерации PDF: {exc}") from exc


@router.get("/{document_id}/preview")
async def get_document_preview(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Convert document PDF pages to PNG images for mobile-friendly viewing."""
    import base64
    import fitz  # PyMuPDF
    from fastapi.responses import Response as FastResponse
    from app.core import s3

    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    pdf_bytes = None
    if doc.pdf_path:
        pdf_bytes = await s3.download_file(doc.pdf_path)

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF не найден")

    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            b64 = base64.b64encode(img_bytes).decode("ascii")
            pages.append({"page": page_num + 1, "data": f"data:image/png;base64,{b64}"})
        pdf_doc.close()
        return {"pages": pages, "total": len(pages)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка конвертации: {exc}") from exc


@router.post("/invoice", response_model=DocumentRead)
async def save_invoice_document(
    payload: SaveInvoiceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DocumentRead:
    invoice = payload.payload
    filename = f"invoice-{''.join(char if char.isascii() and char.isalnum() else '-' for char in invoice.invoice_number).strip('-') or 'document'}.docx"

    try:
        docx_bytes = await render_service.render_invoice_docx(invoice, user_id)
        pdf_bytes = await render_service.convert_docx_to_pdf(filename, docx_bytes)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"render_pipeline_error: {exc}") from exc

    pdf_path = await render_service.save_file(filename.replace(".docx", ".pdf"), pdf_bytes, user_id=user_id)
    docx_path = await render_service.save_file(filename, docx_bytes, user_id=user_id)

    # Parse total amount from string
    try:
        total_amount = float(invoice.total_sum.replace(" ", "").replace(",", "."))
    except (ValueError, AttributeError):
        total_amount = 0.0

    new_doc = Document(
        user_id=user_id,
        title=f"Счет № {invoice.invoice_number}",
        client_name=invoice.client_name,
        total_sum=invoice.total_sum,
        total_amount=total_amount,
        total_sum_in_words=invoice.total_sum_in_words,
        pdf_path=pdf_path,
        docx_path=docx_path,
        payload_json=invoice.model_dump_json(by_alias=True),
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    for item in invoice.items:
        new_item = DocumentItem(
            document_id=new_doc.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            price=item.price,
            total=item.total,
            code=item.code,
        )
        db.add(new_item)

    db.commit()
    db.refresh(new_doc)

    return new_doc


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    db.delete(doc)
    db.commit()
    return {"status": "ok"}
