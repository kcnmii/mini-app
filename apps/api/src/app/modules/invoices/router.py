"""Invoice CRUD router — the core financial entity (Phase 1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user_id
from app.core.db import get_db, Invoice, NewInvoiceItem, Payment, Document
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceRead,
    InvoiceStatusUpdate,
    PaymentCreate,
    PaymentRead,
)
from app.modules.telegram_bot.service import TelegramBotClient
from app.core.scheduler import notify_status_change, send_payment_reminder

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _mark_overdue(db: Session, user_id: int) -> int:
    """Auto-update sent invoices whose due_date has passed to 'overdue'.
    Returns number of rows updated.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    count = (
        db.query(Invoice)
        .filter(
            Invoice.user_id == user_id,
            Invoice.status == "sent",
            Invoice.due_date.isnot(None),
            Invoice.due_date < now,
        )
        .update({"status": "overdue", "updated_at": now}, synchronize_session="fetch")
    )
    if count:
        db.commit()
    return count


# ── LIST ──

@router.get("", response_model=list[InvoiceRead])
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status: draft|sent|paid|overdue"),
    client_id: Optional[int] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[InvoiceRead]:
    _mark_overdue(db, user_id)
    q = db.query(Invoice).options(
        joinedload(Invoice.line_items),
    ).filter(Invoice.user_id == user_id)
    if status:
        q = q.filter(Invoice.status == status)
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    invoices = q.order_by(Invoice.id.desc()).limit(200).all()
    return invoices


# ── CREATE ──

@router.post("", response_model=InvoiceRead, status_code=201)
async def create_invoice(
    payload: InvoiceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InvoiceRead:
    # Calculate total from items
    total = sum(it.total or (it.quantity * it.price) for it in payload.items)

    inv = Invoice(
        user_id=user_id,
        number=payload.number,
        date=payload.date or datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=payload.due_date,
        client_id=payload.client_id,
        client_name=payload.client_name,
        client_bin=payload.client_bin,
        deal_reference=payload.deal_reference,
        payment_code=payload.payment_code,
        status="draft",
        total_amount=total,
    )
    db.add(inv)
    db.flush()

    for it in payload.items:
        item_total = it.total or (it.quantity * it.price)
        line = NewInvoiceItem(
            invoice_id=inv.id,
            catalog_item_id=it.catalog_item_id,
            name=it.name,
            quantity=it.quantity,
            unit=it.unit,
            price=it.price,
            total=item_total,
            code=it.code,
        )
        db.add(line)

    db.commit()
    db.refresh(inv)
    return inv


# ── GET DETAIL ──

@router.get("/next-number")
async def get_next_invoice_number(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    import re
    last = db.query(Invoice).filter(Invoice.user_id == user_id).order_by(Invoice.id.desc()).first()
    if not last:
        return {"next_number": "СФ-001"}
    match = re.search(r"(\d+)", last.number)
    if match:
        padding = len(match.group(1))
        next_num = str(int(match.group(1)) + 1).zfill(padding)
        return {"next_number": f"СФ-{next_num}"}
    return {"next_number": "СФ-001"}


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InvoiceRead:
    inv = (
        db.query(Invoice)
        .options(joinedload(Invoice.line_items))
        .filter(Invoice.id == invoice_id, Invoice.user_id == user_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    return inv


# ── UPDATE STATUS ──

VALID_STATUSES = {"draft", "sent", "paid", "overdue"}

@router.patch("/{invoice_id}/status", response_model=InvoiceRead)
async def update_invoice_status(
    invoice_id: int,
    body: InvoiceStatusUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InvoiceRead:
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {body.status}")

    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    old_status = inv.status
    inv.status = body.status
    inv.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(inv)

    # Push notification on status change (sent, overdue)
    if old_status != body.status and body.status in ("sent", "overdue"):
        try:
            await notify_status_change(user_id, inv, body.status)
        except Exception as e:
            print(f"Status notification failed: {e}")

    return inv


# ── MARK AS PAID ──

@router.post("/{invoice_id}/pay", response_model=PaymentRead, status_code=201)
async def mark_invoice_paid(
    invoice_id: int,
    body: PaymentCreate = PaymentCreate(),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PaymentRead:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    payment_amount = body.amount if body.amount is not None else inv.total_amount

    payment = Payment(
        user_id=user_id,
        invoice_id=inv.id,
        amount=payment_amount,
        date=body.date or datetime.now(timezone.utc).replace(tzinfo=None),
        source="manual",
        note=body.note,
    )
    db.add(payment)

    inv.status = "paid"
    inv.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(payment)

    # Telegram notification
    bot = TelegramBotClient()
    try:
        msg = (
            f"✅ <b>Оплата получена!</b> (вручную)\n\n"
            f"Счет: <code>{inv.number}</code>\n"
            f"Клиент: <code>{inv.client_name}</code>\n"
            f"Сумма: <b>{payment_amount:,.2f} ₸</b>\n\n"
            f"<i>Статус счета обновлен на 'Оплачен'.</i>"
        )
        await bot.send_message(chat_id=user_id, text=msg)
    except Exception as e:
        print(f"Failed to send telegram notification: {e}")
    finally:
        await bot.close()

    return payment


# ── DELETE ──

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    db.delete(inv)
    db.commit()
    return {"status": "ok"}


# ── REMIND ABOUT PAYMENT ──

@router.post("/{invoice_id}/remind")
async def remind_about_payment(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Send a payment reminder for an invoice via Telegram.
    
    The reminder is sent to the user's Telegram chat.
    They can forward it to the client.
    """
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    
    if inv.status == "paid":
        raise HTTPException(status_code=400, detail="Счёт уже оплачен")
    
    try:
        reminder_text = await send_payment_reminder(user_id=user_id, invoice=inv)
        return {"status": "ok", "message": "Напоминание отправлено в Telegram"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки: {e}")


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Serve PDF for an invoice. Auto-regenerates if file is missing from disk."""
    import json
    from app.core import s3
    from app.modules.render.service import RenderService
    from app.schemas.render import InvoiceRenderPayload

    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    # Find the matching Document record (specifically the Invoice, not Acts/Waybills)
    doc = db.query(Document).filter(
        Document.user_id == user_id,
        Document.title.like(f"Счет %{inv.number}%")
    ).order_by(Document.id.desc()).first()

    # If document exists and PDF file is in S3 — return it immediately
    if doc and doc.pdf_path:
        pdf_bytes = await s3.download_file(doc.pdf_path)
        if pdf_bytes:
            return Response(pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="invoice_{inv.number}.pdf"'})

    # Otherwise, regenerate PDF from stored payload_json
    payload_json = doc.payload_json if doc and doc.payload_json else None
    if not payload_json:
        raise HTTPException(status_code=404, detail="Нет данных для генерации PDF. Пересохраните счет.")

    try:
        payload_data = json.loads(payload_json)
        render_payload = InvoiceRenderPayload(**payload_data)
        render_service = RenderService()

        safe_number = ''.join(c if c.isascii() and c.isalnum() else '-' for c in inv.number).strip('-') or 'document'
        filename = f"invoice-{safe_number}.docx"

        docx_bytes = await render_service.render_invoice_docx(render_payload, user_id)
        pdf_bytes = await render_service.convert_docx_to_pdf(filename, docx_bytes)

        pdf_path = await render_service.save_file(filename.replace(".docx", ".pdf"), pdf_bytes, user_id=user_id)
        docx_path = await render_service.save_file(filename, docx_bytes, user_id=user_id)

        # Update document record with new paths
        if doc:
            doc.pdf_path = pdf_path
            doc.docx_path = docx_path
            db.commit()

        return Response(pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="invoice_{inv.number}.pdf"'})

    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка генерации PDF: {exc}") from exc


@router.get("/{invoice_id}/preview")
async def get_invoice_preview(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Convert invoice PDF pages to PNG images for mobile-friendly viewing."""
    import json
    import base64
    import fitz  # PyMuPDF
    from app.core import s3
    from app.modules.render.service import RenderService
    from app.schemas.render import InvoiceRenderPayload

    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    # Find the matching Document record (specifically the Invoice, not Acts/Waybills)
    doc = db.query(Document).filter(
        Document.user_id == user_id,
        Document.title.like(f"Счет %{inv.number}%")
    ).order_by(Document.id.desc()).first()

    pdf_bytes = None
    if doc and doc.pdf_path:
        pdf_bytes = await s3.download_file(doc.pdf_path)

    # If PDF file is missing — regenerate it
    if not pdf_bytes:
        payload_json = doc.payload_json if doc and doc.payload_json else None
        if not payload_json:
            raise HTTPException(status_code=404, detail="Нет данных для генерации превью")

        try:
            payload_data = json.loads(payload_json)
            render_payload = InvoiceRenderPayload(**payload_data)
            render_service = RenderService()

            safe_number = ''.join(c if c.isascii() and c.isalnum() else '-' for c in inv.number).strip('-') or 'document'
            filename = f"invoice-{safe_number}.docx"

            docx_bytes = await render_service.render_invoice_docx(render_payload, user_id)
            pdf_bytes = await render_service.convert_docx_to_pdf(filename, docx_bytes)

            pdf_path = await render_service.save_file(filename.replace(".docx", ".pdf"), pdf_bytes, user_id=user_id)
            docx_path = await render_service.save_file(filename, docx_bytes, user_id=user_id)

            if doc:
                doc.pdf_path = pdf_path
                doc.docx_path = docx_path
                db.commit()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Ошибка генерации: {exc}") from exc

    # Convert PDF pages to PNG images using PyMuPDF
    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            # Render at 2x resolution for crisp display on Retina
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            b64 = base64.b64encode(img_bytes).decode("ascii")
            pages.append({"page": page_num + 1, "data": f"data:image/png;base64,{b64}"})
        pdf_doc.close()
        return {"pages": pages, "total": len(pages)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка конвертации: {exc}") from exc


# ── GENERATE ACT / WAYBILL FROM INVOICE ──

@router.post("/{invoice_id}/generate-document")
async def generate_document_from_invoice(
    invoice_id: int,
    doc_type: str = Query(..., description="act or waybill"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate an Act (АВР) or Waybill (Накладная) based on an existing invoice.

    Renders DOCX+PDF, saves document record, and sends to user via Telegram.
    """
    from app.modules.render.service import RenderService
    from app.core.db import SupplierProfile, Client, ClientContact

    if doc_type not in ("act", "waybill"):
        raise HTTPException(status_code=400, detail="doc_type must be 'act' or 'waybill'")

    inv = (
        db.query(Invoice)
        .options(joinedload(Invoice.line_items))
        .filter(Invoice.id == invoice_id, Invoice.user_id == user_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    # Load supplier profile
    profile = db.query(SupplierProfile).filter(SupplierProfile.user_id == user_id).first()

    # Load client info
    client = None
    client_phone = ""
    client_address = ""
    if inv.client_id:
        client = db.query(Client).filter(Client.id == inv.client_id).first()
        if client:
            client_address = client.address or ""
            # Get first contact phone
            contact = db.query(ClientContact).filter(ClientContact.client_id == client.id).first()
            if contact:
                client_phone = contact.phone or ""

    # Build items list
    items = []
    total_quantity = 0.0
    for i, li in enumerate(inv.line_items):
        items.append({
            "index": i + 1,
            "name": li.name,
            "unit": li.unit or "шт.",
            "quantity": str(li.quantity),
            "price": f"{li.price:,.0f}",
            "total": f"{li.total:,.0f}",
            "tax": "0",
        })
        total_quantity += li.quantity

    total_sum_formatted = f"{inv.total_amount:,.0f}"

    # Number to words (simple Russian)
    def _num_to_words_simple(n: int) -> str:
        if n == 0:
            return "ноль"
        units = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
        teens = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
        tens = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
        hundreds = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]

        parts = []
        if n >= 1000:
            t = n // 1000
            if t == 1:
                parts.append("одна тысяча")
            elif t == 2:
                parts.append("две тысячи")
            elif 3 <= t <= 4:
                parts.append(f"{units[t]} тысячи")
            elif 5 <= t <= 20:
                parts.append(f"{units[t] if t < 10 else teens[t - 10]} тысяч")
            else:
                parts.append(f"{t} тысяч")
            n %= 1000

        if n >= 100:
            parts.append(hundreds[n // 100])
            n %= 100

        if 10 <= n <= 19:
            parts.append(teens[n - 10])
        else:
            if n >= 20:
                parts.append(tens[n // 10])
                n %= 10
            if n > 0:
                parts.append(units[n])

        return " ".join(p for p in parts if p)

    total_sum_words = _num_to_words_simple(int(inv.total_amount)) + " тенге"
    total_qty_int = int(total_quantity)
    total_qty_words = _num_to_words_simple(total_qty_int)

    now_str = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%d.%m.%Y")

    import re
    # Determine sequential number for the document based on doc_type field, not title
    prefix = "АВР" if doc_type == "act" else "НКЛ"
    
    # Count existing documents of this type for the user
    existing_count = db.query(Document).filter(
        Document.user_id == user_id,
        Document.doc_type == doc_type,
    ).count()
    
    next_num_str = str(existing_count + 1).zfill(3)
    doc_number = f"{prefix}-{next_num_str}"

    if doc_type == "act":
        template_key = "act-kz"
        doc_title = f"{doc_number}"
        data = {
            "MyCompanyRequisiteRqCompanyName": (profile.company_name if profile else "") or "",
            "MyCompanyRequisiteRegisteredAddressText": (profile.supplier_address if profile else "") or "",
            "MyCompanyPhone": (profile.phone if profile else "") or "",
            "MyCompanyRequisiteRqDirector": (profile.executor_name if profile else "") or "",
            "ClientName": inv.client_name or "",
            "ClientPhone": client_phone,
            "RequisiteRegisteredAddressText": client_address,
            "DocumentNumber": doc_number,
            "TotalQuantity": str(total_qty_int),
            "TotalSum": total_sum_formatted,
            "items": items,
        }
    else:
        template_key = "waybill-kz"
        doc_title = f"{doc_number}"
        data = {
            "MyCompanyRequisiteRqCompanyName": (profile.company_name if profile else "") or "",
            "MyCompanyRequisiteRqBin": (profile.company_iin if profile else "") or "",
            "MyCompanyRequisiteRqAccountant": (profile.executor_name if profile else "") or "",
            "RequisiteRqCompanyName": inv.client_name or "",
            "DocumentNumber": doc_number,
            "DocumentCreateTime": now_str,
            "TotalQuantity": str(total_qty_int),
            "TotalQuantityWords": total_qty_words,
            "TotalSum": total_sum_formatted,
            "TotalSumWords": total_sum_words,
            "TotalTax": "0",
            "items": items,
        }

    render_service = RenderService()

    try:
        # Render DOCX
        docx_bytes = await render_service.render_document_docx(template_key, data)

        safe_number = ''.join(c if c.isascii() and c.isalnum() else '-' for c in doc_number).strip('-') or 'document'
        filename_prefix = f"{doc_type}-{safe_number}"

        # Convert to PDF
        pdf_bytes = await render_service.convert_docx_to_pdf(f"{filename_prefix}.docx", docx_bytes)

        # Save to S3
        pdf_path = await render_service.save_file(f"{filename_prefix}.pdf", pdf_bytes, user_id=user_id)
        docx_path = await render_service.save_file(f"{filename_prefix}.docx", docx_bytes, user_id=user_id)

        # Save document record with correct doc_type
        doc_record = Document(
            user_id=user_id,
            title=doc_title,
            client_name=inv.client_name or "",
            total_sum=total_sum_formatted,
            total_amount=inv.total_amount,
            total_sum_in_words=total_sum_words,
            pdf_path=pdf_path,
            docx_path=docx_path,
            doc_type=doc_type,  # ← Critical: set doc_type for proper counting
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        # Send via Telegram
        bot = TelegramBotClient()
        try:
            await bot.send_invoice_documents(
                chat_id=user_id,
                filename_prefix=filename_prefix,
                pdf_bytes=pdf_bytes,
                docx_bytes=docx_bytes,
                caption=f"{'📋 Акт выполненных работ' if doc_type == 'act' else '📦 Накладная'}\n{doc_title}\nКлиент: {inv.client_name}\nСумма: {total_sum_formatted} ₸",
                user_id=user_id,
            )
        except Exception as e:
            # Don't fail the whole request if Telegram send fails
            pass
        finally:
            await bot.close()

        return {
            "status": "ok",
            "doc_type": doc_type,
            "title": doc_title,
            "pdf_path": pdf_path,
            "docx_path": docx_path,
            "document_id": doc_record.id,
        }

    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка генерации документа: {exc}") from exc
