from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import httpx
import os

from app.core.db import get_db, Document, DocumentItem
from app.core.auth import get_current_user_id
from app.modules.render.service import RenderService
from app.schemas.document import DocumentRead, SaveInvoiceRequest

router = APIRouter(prefix="/documents", tags=["documents"])
render_service = RenderService()


@router.get("/recent", response_model=list[DocumentRead])
async def list_recent_documents(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    docs = db.query(Document).filter(Document.user_id == user_id).order_by(Document.id.desc()).limit(50).all()
    return docs


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
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc or not doc.pdf_path or not os.path.exists(doc.pdf_path):
        raise HTTPException(status_code=404, detail="PDF не найден")

    filename = os.path.basename(doc.pdf_path)
    return FileResponse(doc.pdf_path, media_type="application/pdf", filename=filename)


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

    pdf_path = render_service.persist_debug_output(filename.replace(".docx", ".pdf"), pdf_bytes)

    new_doc = Document(
        user_id=user_id,
        title=f"Счет № {invoice.invoice_number}",
        client_name=invoice.client_name,
        total_sum=invoice.total_sum,
        total_sum_in_words=invoice.total_sum_in_words,
        pdf_path=pdf_path,
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
