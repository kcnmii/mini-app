from fastapi import APIRouter, HTTPException, Response, Depends
import httpx
from sqlalchemy.orm import Session
from app.core.db import get_db

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
    db: Session = Depends(get_db),
) -> TelegramSendInvoiceResponse:
    invoice_payload = payload.payload or _sample_invoice_payload()
    filename = f"invoice-{''.join(char if char.isascii() and char.isalnum() else '-' for char in invoice_payload.invoice_number).strip('-') or 'document'}.pdf"

    try:
        docx_bytes = await render_service.render_invoice_docx(invoice_payload, user_id)
        # Store for telegram callback
        await render_service.save_file(filename.replace(".pdf", ".docx"), docx_bytes, user_id=user_id)
        
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
            user_id=user_id,
        )
        
        # --- NEW LOGIC: Send to counterparty's "Incoming" if they exist ---
        client_iin = getattr(invoice_payload, "client_iin", None) or getattr(invoice_payload, "CLIENT_IIN", None)
        if isinstance(invoice_payload, dict):
            client_iin = invoice_payload.get("CLIENT_IIN") or invoice_payload.get("client_iin")
            
        if client_iin and isinstance(client_iin, str):
            clean_bin = client_iin.strip()
            if len(clean_bin) == 12:
                from app.core.db import Invoice, SupplierProfile, NewInvoiceItem
                from datetime import datetime, timezone
                import uuid
                
                target_profiles = db.query(SupplierProfile).filter(SupplierProfile.company_iin == clean_bin).all()
                for target_profile in target_profiles:
                    if target_profile and target_profile.user_id != user_id:
                        sender_profile = db.query(SupplierProfile).filter(SupplierProfile.user_id == user_id).first()
                        sender_name = sender_profile.company_name if sender_profile else "Неизвестно"
                        sender_bin = sender_profile.company_iin if sender_profile else ""
                        
                        now = datetime.now(timezone.utc).replace(tzinfo=None)
                        invoice_number = f"ВХОД-{str(uuid.uuid4()).replace('-', '')[:6].upper()}"
                        
                        # Calculate total from payload items
                        items = getattr(invoice_payload, "items", [])
                        if isinstance(invoice_payload, dict):
                            items = invoice_payload.get("items", [])
                        
                        def parse_amt(val) -> float:
                            if not val: return 0.0
                            if isinstance(val, str):
                                val = val.replace("\xa0", "").replace(" ", "").replace(",", ".")
                            try:
                                return float(val)
                            except:
                                return 0.0
                        
                        total_amount = 0.0
                        for it in items:
                            q_val = it.get("quantity", 0) if isinstance(it, dict) else getattr(it, "quantity", 0)
                            p_val = it.get("price", 0) if isinstance(it, dict) else getattr(it, "price", 0)
                            total_amount += parse_amt(q_val) * parse_amt(p_val)
                        
                        inv = Invoice(
                            user_id=target_profile.user_id,
                            number=invoice_number,
                            date=now,
                            client_name=sender_name,
                            client_bin=sender_bin,
                            status="incoming",
                            total_amount=total_amount,
                            created_at=now,
                            updated_at=now
                        )
                        db.add(inv)
                        db.flush()
                        
                        for it in items:
                            q_val = it.get("quantity", 0) if isinstance(it, dict) else getattr(it, "quantity", 0)
                            p_val = it.get("price", 0) if isinstance(it, dict) else getattr(it, "price", 0)
                            n = it.get("name", "") if isinstance(it, dict) else getattr(it, "name", "")
                            u = it.get("unit", "шт") if isinstance(it, dict) else getattr(it, "unit", "шт")
                            
                            q = parse_amt(q_val)
                            p = parse_amt(p_val)
                            line = NewInvoiceItem(
                                invoice_id=inv.id,
                                name=n,
                                quantity=str(q),
                                price=str(p),
                                total=str(q * p),
                                unit=u
                            )
                            db.add(line)
                            
                        db.commit()
                        
                        # Send notification to target
                        try:
                            from app.services.edo_notifications import notify_incoming_invoice
                            await notify_incoming_invoice(db, target_profile.user_id, inv, sender_name)
                        except Exception as e:
                            import logging
                            logging.getLogger(__name__).warning(f"Failed to notify incoming invoice: {e}")
        # -------------------------------------------------------------------

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
