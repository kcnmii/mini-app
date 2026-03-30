"""
EDO (Electronic Document Management) Module — Router.

Handles:
  - Initiating ЭЦП signing via SIGEX + eGov Mobile
  - Checking signing status (polling)
  - Saving CMS signatures to DB
  - Sharing documents with counterparties (link generation)
  - Public guest view of shared documents
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.db import (
    get_db,
    Document,
    Signature,
    SigningSession,
    DocumentShare,
    SupplierProfile,
)
from app.services.sigex_client import SigexClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/edo", tags=["edo"])

sigex = SigexClient()


# ── Pydantic Schemas ──

class SignDocumentRequest(BaseModel):
    document_id: int
    signer_role: str = "sender"  # sender | receiver


class SignNcaRequest(BaseModel):
    document_id: int
    cms_signature_b64: str
    signer_role: str = "sender"
    signer_iin: str = ""
    signer_name: str = ""
    signer_org: str = ""
    certificate_serial: str = ""


class SignDocumentResponse(BaseModel):
    signing_session_id: int
    egov_mobile_link: str
    egov_business_link: str
    qr_code_b64: str


class SigningStatusResponse(BaseModel):
    status: str  # pending | signed | expired | error
    signed_at: str | None = None
    signer_name: str | None = None


class ShareDocumentRequest(BaseModel):
    document_id: int
    share_type: str = "link"  # link | email | telegram
    recipient_email: str = ""
    recipient_name: str = ""
    recipient_bin: str = ""


class ShareDocumentResponse(BaseModel):
    share_url: str
    share_uuid: str


class PublicDocumentResponse(BaseModel):
    title: str
    client_name: str
    total_sum: str
    doc_type: str
    edo_status: str
    sender_name: str
    sender_bin: str
    created_at: str
    md5_hash: str
    signatures: list[dict]
    pdf_available: bool


# ──────────────────────────────────────────────
# POST /edo/sign — Initiate ЭЦП signing
# ──────────────────────────────────────────────
@router.post("/sign", response_model=SignDocumentResponse)
async def initiate_signing(
    req: SignDocumentRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Start the ЭЦП signing process for a document.
    
    Split into 2 phases:
      Phase 1 (sync): Register signing on SIGEX → return deeplinks immediately
      Phase 2 (background): Send document data + poll for CMS signature
    
    This prevents the API from timing out — SIGEX's dataURL POST
    is a long-polling endpoint that blocks until eGov Mobile connects.
    """
    doc = db.query(Document).filter(
        Document.id == req.document_id,
        Document.user_id == user_id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Get PDF bytes for signing
    from app.core import s3
    pdf_bytes = None
    if doc.pdf_path:
        pdf_bytes = await s3.download_file(doc.pdf_path)

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF документа не найден для подписания")

    # Compute MD5 hash
    import base64
    md5_hash = hashlib.md5(pdf_bytes).hexdigest()
    doc.md5_hash = md5_hash
    document_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    # Load supplier profile for metadata
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.user_id == user_id
    ).first()

    signer_name = (profile.executor_name if profile else "") or "Подписант"
    signer_iin = (profile.company_iin if profile else "") or ""
    company_name = (profile.company_name if profile else "") or ""

    meta = [
        {"name": "Документ", "value": doc.title},
        {"name": "Сумма", "value": doc.total_sum},
        {"name": "Компания", "value": company_name},
    ]

    # ── Phase 1: Register on SIGEX (fast, ~1-2 seconds) ──
    try:
        reg = await sigex.register_signing(
            description=f"Подписание: {doc.title}",
        )
    except Exception as exc:
        logger.error("SIGEX register_signing failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Ошибка SIGEX: {exc}") from exc

    # Save signing session
    session = SigningSession(
        document_id=doc.id,
        user_id=user_id,
        sign_url=reg.get("signURL", ""),
        egov_mobile_link=reg.get("eGovMobileLaunchLink", ""),
        egov_business_link=reg.get("eGovBusinessLaunchLink", ""),
        qr_code_b64=reg.get("qrCode", ""),
        status="pending",
        signer_role=req.signer_role,
    )
    db.add(session)

    # Update document status
    doc.edo_status = "awaiting_sign"
    db.commit()
    db.refresh(session)

    # ── Phase 2: Send data + poll in background ──
    background_tasks.add_task(
        _send_data_and_poll,
        signing_session_id=session.id,
        data_url=reg.get("dataURL", ""),
        sign_url=reg.get("signURL", ""),
        document_b64=document_b64,
        names=[doc.title, doc.title, doc.title],
        meta=meta,
        document_id=doc.id,
        user_id=user_id,
        signer_iin=signer_iin,
        signer_name=signer_name,
        signer_role=req.signer_role,
    )

    return SignDocumentResponse(
        signing_session_id=session.id,
        egov_mobile_link=reg.get("eGovMobileLaunchLink", ""),
        egov_business_link=reg.get("eGovBusinessLaunchLink", ""),
        qr_code_b64=reg.get("qrCode", ""),
    )


# ──────────────────────────────────────────────
# GET /edo/signing-status/{session_id}
# ──────────────────────────────────────────────
@router.get("/signing-status/{session_id}", response_model=SigningStatusResponse)
async def get_signing_status(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Check signing status for a given session."""
    session = db.query(SigningSession).filter(
        SigningSession.id == session_id,
        SigningSession.user_id == user_id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия подписания не найдена")

    result = SigningStatusResponse(status=session.status)

    if session.status == "signed":
        sig = db.query(Signature).filter(
            Signature.document_id == session.document_id,
            Signature.signer_role == session.signer_role,
        ).order_by(Signature.id.desc()).first()
        if sig:
            result.signed_at = sig.signed_at.isoformat() if sig.signed_at else None
            result.signer_name = sig.signer_name

    return result


# ──────────────────────────────────────────────
# GET /edo/pdf-b64/{document_id} — Get PDF for NCALayer signing
# ──────────────────────────────────────────────
@router.get("/pdf-b64/{document_id}")
async def get_document_pdf_b64(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id,
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
        
    if not doc.pdf_path:
        raise HTTPException(status_code=400, detail="PDF не сформирован")
        
    from app.core import s3
    pdf_bytes = await s3.download_file(doc.pdf_path)
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Файл документа отсутствует")
        
    import base64
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    return {"success": True, "pdf_b64": b64}


# ──────────────────────────────────────────────
# POST /edo/sign/nca — Save NCALayer signature directly
# ──────────────────────────────────────────────
@router.post("/sign/nca")
async def save_nca_signature(
    req: SignNcaRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from fastapi.responses import JSONResponse
    doc = db.query(Document).filter(
        Document.id == req.document_id,
        Document.user_id == user_id,
    ).first()
    
    if not doc:
        return JSONResponse({"success": False, "error": "Документ не найден"}, status_code=404)
        
    # Verify the CMS document matches SIGEX
    try:
        cms_info = await sigex.get_signature_info(req.cms_signature_b64)
    except Exception as exc:
        logger.error("NCALayer CMS validation failed: %s", exc)
        return JSONResponse({"success": False, "error": f"Ошибка проверки подписи: {exc}"}, status_code=400)

    cert_info = None
    if cms_info and isinstance(cms_info, list) and len(cms_info) > 0:
        cert_info = cms_info[0]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sig = Signature(
        document_id=doc.id,
        signer_iin=req.signer_iin or (cert_info.subject_iin if cert_info else ""),
        signer_name=req.signer_name or (cert_info.subject_cn if cert_info else "Пользователь"),
        signer_org_name=req.signer_org or (cert_info.subject_org if cert_info else ""),
        signer_role=req.signer_role,
        certificate_serial=req.certificate_serial or (cert_info.serial_hex if cert_info else ""),
        certificate_valid_from=cert_info.valid_from.replace(tzinfo=None) if cert_info and cert_info.valid_from else None,
        certificate_valid_to=cert_info.valid_to.replace(tzinfo=None) if cert_info and cert_info.valid_to else None,
        signature_data=req.cms_signature_b64,
        signed_at=now,
    )
    db.add(sig)

    if req.signer_role == "sender":
        doc.edo_status = "signed_self"
        if not doc.signed_at:
            doc.signed_at = now
    else:
        doc.edo_status = "signed_both"
        if not doc.countersigned_at:
            doc.countersigned_at = now

    db.commit()

    # If sender and link is standard, you might also share it dynamically
    # For now, just mark signed_self
    return {"success": True, "message": "Документ успешно подписан"}


# ──────────────────────────────────────────────
# GET /edo/incoming — Documents sent TO the current user
# ──────────────────────────────────────────────
@router.get("/incoming")
async def get_incoming_documents(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get documents that were sent TO the current user.
    Matching is done by IIN/BIN: document.receiver_bin == profile.company_iin.
    """
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.user_id == user_id
    ).first()

    if not profile or not (profile.company_iin or "").strip():
        return []

    my_iin = profile.company_iin.strip()

    # Find documents where receiver_bin matches MY IIN/BIN
    # AND the document was signed by sender (at least signed_self)
    # AND the document is NOT mine (sender is different user)
    docs = db.query(Document).filter(
        Document.receiver_bin == my_iin,
        Document.user_id != user_id,
        Document.edo_status.in_(["signed_self", "sent", "signed_both", "rejected"]),
    ).order_by(Document.created_at.desc()).limit(100).all()

    result = []
    for d in docs:
        # Get sender info
        sender_profile = db.query(SupplierProfile).filter(
            SupplierProfile.user_id == d.user_id
        ).first()
        sender_name = (sender_profile.company_name if sender_profile else "") or "Неизвестный"
        sender_bin = (sender_profile.company_iin if sender_profile else "") or ""

        # Get or create share for this doc
        share = db.query(DocumentShare).filter(
            DocumentShare.document_id == d.id
        ).first()
        share_uuid = share.share_uuid if share else None

        result.append({
            "id": d.id,
            "title": d.title,
            "client_name": d.client_name,
            "total_sum": d.total_sum,
            "doc_type": d.doc_type or "invoice",
            "edo_status": d.edo_status or "draft",
            "created_at": d.created_at.isoformat() if d.created_at else "",
            "sender_name": sender_name,
            "sender_bin": sender_bin,
            "share_uuid": share_uuid,
            "is_incoming": True,
        })

    return result


# ──────────────────────────────────────────────
# POST /edo/share — Share document with counterparty
# ──────────────────────────────────────────────
@router.post("/share", response_model=ShareDocumentResponse)
async def share_document(
    req: ShareDocumentRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate a shareable link for a document."""
    doc = db.query(Document).filter(
        Document.id == req.document_id,
        Document.user_id == user_id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    share_id = str(uuid.uuid4())

    share = DocumentShare(
        document_id=doc.id,
        share_uuid=share_id,
        share_type=req.share_type,
        recipient_email=req.recipient_email,
        recipient_name=req.recipient_name,
        recipient_bin=req.recipient_bin,
    )
    db.add(share)

    # Update document receiver info
    if req.recipient_bin:
        doc.receiver_bin = req.recipient_bin
    if req.recipient_name:
        doc.receiver_name = req.recipient_name
    if doc.edo_status == "signed_self":
        doc.edo_status = "sent"

    db.commit()

    # Notify receiver if they are a registered user
    background_tasks.add_task(_notify_incoming_async, doc.id)

    # The share URL will be served by the frontend or a public API
    share_url = f"/doc/{share_id}"

    return ShareDocumentResponse(share_url=share_url, share_uuid=share_id)


# ──────────────────────────────────────────────
# GET /edo/public/{share_uuid} — Guest document view (no auth required)
# ──────────────────────────────────────────────
@router.get("/public/{share_uuid}", response_model=PublicDocumentResponse)
async def get_public_document(
    share_uuid: str,
    db: Session = Depends(get_db),
):
    """
    Public endpoint — no authentication required.
    Returns document info, signatures, and PDF availability for counterparty.
    """
    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()

    if not share:
        raise HTTPException(status_code=404, detail="Документ не найден или ссылка недействительна")

    # Mark as accessed
    if not share.accessed_at:
        share.accessed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ удалён")

    # Get sender profile
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.user_id == doc.user_id
    ).first()

    sender_name = (profile.company_name if profile else "") or ""
    sender_bin = (profile.company_iin if profile else "") or ""

    # Get signatures
    sigs = db.query(Signature).filter(
        Signature.document_id == doc.id,
    ).all()

    signatures_list = [
        {
            "signer_name": s.signer_name,
            "signer_iin": s.signer_iin,
            "signer_org": s.signer_org_name,
            "signer_role": s.signer_role,
            "certificate_serial": s.certificate_serial,
            "signed_at": s.signed_at.isoformat() if s.signed_at else None,
        }
        for s in sigs
    ]

    return PublicDocumentResponse(
        title=doc.title,
        client_name=doc.client_name,
        total_sum=doc.total_sum,
        doc_type=doc.doc_type or "invoice",
        edo_status=doc.edo_status or "draft",
        sender_name=sender_name,
        sender_bin=sender_bin,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        md5_hash=doc.md5_hash or "",
        signatures=signatures_list,
        pdf_available=bool(doc.pdf_path),
    )


# ──────────────────────────────────────────────
# GET /edo/document/{document_id}/signatures
# ──────────────────────────────────────────────
@router.get("/document/{document_id}/signatures")
async def get_document_signatures(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all signatures for a document."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    sigs = db.query(Signature).filter(
        Signature.document_id == document_id,
    ).order_by(Signature.signed_at.asc()).all()

    return {
        "document_id": document_id,
        "edo_status": doc.edo_status,
        "md5_hash": doc.md5_hash,
        "signatures": [
            {
                "id": s.id,
                "signer_name": s.signer_name,
                "signer_iin": s.signer_iin,
                "signer_org": s.signer_org_name,
                "signer_role": s.signer_role,
                "certificate_serial": s.certificate_serial,
                "certificate_valid_from": s.certificate_valid_from.isoformat() if s.certificate_valid_from else None,
                "certificate_valid_to": s.certificate_valid_to.isoformat() if s.certificate_valid_to else None,
                "signed_at": s.signed_at.isoformat() if s.signed_at else None,
                "signature_type": s.signature_type,
            }
            for s in sigs
        ],
    }


# ──────────────────────────────────────────────
# Background task: Send data to SIGEX + poll for signature
# ──────────────────────────────────────────────
async def _send_data_and_poll(
    signing_session_id: int,
    data_url: str,
    sign_url: str,
    document_b64: str,
    names: list[str],
    meta: list[dict[str, str]],
    document_id: int,
    user_id: int,
    signer_iin: str,
    signer_name: str,
    signer_role: str,
):
    """
    Background task:
      1. Send document data to SIGEX (long-polling, retries)
      2. Poll for CMS signature
      3. Save signature to DB
    """
    from app.core.db import SessionLocal

    # Phase 2a: Send data to SIGEX
    try:
        await sigex.send_data_to_sign(
            data_url=data_url,
            document_b64=document_b64,
            names=names,
            meta=meta,
            mime="@file/pdf",  # eGov Mobile shows PDF preview before signing
        )
        logger.info("SIGEX data sent for document %d", document_id)
    except Exception as exc:
        logger.error("SIGEX send_data failed for document %d: %s", document_id, exc)
        db = SessionLocal()
        try:
            session = db.query(SigningSession).filter(
                SigningSession.id == signing_session_id
            ).first()
            if session:
                session.status = "error"
            db.commit()
        finally:
            db.close()
        return

    # Phase 2b: Poll for signature
    await _poll_and_save_signature(
        signing_session_id=signing_session_id,
        sign_url=sign_url,
        document_id=document_id,
        user_id=user_id,
        signer_iin=signer_iin,
        signer_name=signer_name,
        signer_role=signer_role,
    )


# ──────────────────────────────────────────────
# Background task: Poll SIGEX for signature
# ──────────────────────────────────────────────
async def _poll_and_save_signature(
    signing_session_id: int,
    sign_url: str,
    document_id: int,
    user_id: int,
    signer_iin: str,
    signer_name: str,
    signer_role: str,
):
    """Background task that polls SIGEX until signature arrives, then saves it."""
    from app.core.db import SessionLocal

    try:
        signatures = await sigex.poll_signatures(
            sign_url=sign_url,
            max_wait_seconds=300,  # 5 minutes
            poll_interval=3.0,
        )

        if not signatures:
            raise Exception("Пустой список подписей")

        cms_signature_b64 = signatures[0]

        # Extract certificate metadata from CMS signature
        from app.services.cms_parser import parse_cms_signature
        cert_info = parse_cms_signature(cms_signature_b64)

        # ── SECURITY: Validate signer identity ──
        db = SessionLocal()
        try:
            cert_iin = (cert_info.subject_iin if cert_info else "").strip()

            if signer_role == "sender":
                # Sender: IIN from certificate must match profile IIN
                profile = db.query(SupplierProfile).filter(
                    SupplierProfile.user_id == user_id
                ).first()
                expected_iin = (profile.company_iin if profile else "").strip() if profile else ""

                if expected_iin and cert_iin and cert_iin != expected_iin:
                    logger.warning(
                        "SECURITY: Sender IIN mismatch! Profile=%s, Certificate=%s, doc=%d",
                        expected_iin, cert_iin, document_id,
                    )
                    session = db.query(SigningSession).filter(
                        SigningSession.id == signing_session_id
                    ).first()
                    if session:
                        session.status = "error"
                    db.commit()
                    return  # Reject the signature

            elif signer_role == "receiver":
                # Receiver: IIN from certificate must match document receiver_bin
                doc_check = db.query(Document).filter(Document.id == document_id).first()
                expected_receiver = (doc_check.receiver_bin if doc_check else "").strip() if doc_check else ""

                if expected_receiver and cert_iin and cert_iin != expected_receiver:
                    logger.warning(
                        "SECURITY: Receiver IIN mismatch! Expected=%s, Certificate=%s, doc=%d",
                        expected_receiver, cert_iin, document_id,
                    )
                    session = db.query(SigningSession).filter(
                        SigningSession.id == signing_session_id
                    ).first()
                    if session:
                        session.status = "error"
                    db.commit()
                    return  # Reject the signature

            # ── Identity verified — save signature ──
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            sig = Signature(
                document_id=document_id,
                signer_iin=cert_iin or signer_iin,
                signer_name=cert_info.subject_cn if cert_info else signer_name,
                signer_org_name=cert_info.subject_org if cert_info else "",
                signer_role=signer_role,
                signature_data=cms_signature_b64,
                signature_type="cms",
                certificate_serial=cert_info.serial_hex if cert_info else "",
                certificate_valid_from=cert_info.valid_from.replace(tzinfo=None) if cert_info and cert_info.valid_from else None,
                certificate_valid_to=cert_info.valid_to.replace(tzinfo=None) if cert_info and cert_info.valid_to else None,
                signed_at=now,
            )
            db.add(sig)

            # Update signing session
            session = db.query(SigningSession).filter(
                SigningSession.id == signing_session_id
            ).first()
            if session:
                session.status = "signed"

            # Update document status
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                if signer_role == "sender":
                    doc.edo_status = "signed_self"
                    doc.signed_at = now
                elif signer_role == "receiver":
                    doc.countersigned_at = now
                    # Check if both sides signed
                    sender_sig = db.query(Signature).filter(
                        Signature.document_id == document_id,
                        Signature.signer_role == "sender",
                    ).first()
                    if sender_sig:
                        doc.edo_status = "signed_both"

            db.commit()
            logger.info(
                "Signature saved for document %d, signer=%s (IIN=%s), role=%s",
                document_id, cert_info.subject_cn if cert_info else signer_name, cert_iin, signer_role,
            )

            # Auto-stamp PDF when both parties have signed
            try:
                from app.services.stamp_trigger import maybe_stamp_document
                await maybe_stamp_document(db, document_id)
            except Exception as stamp_err:
                logger.warning("PDF stamp failed (non-critical): %s", stamp_err)

            # Notify document owner that counterparty signed
            if signer_role == "receiver" and doc and doc.edo_status == "signed_both":
                try:
                    from app.services.edo_notifications import notify_document_countersigned
                    signer_display = cert_info.subject_cn if cert_info else signer_name
                    await notify_document_countersigned(db, doc, signer_display)
                except Exception as notif_err:
                    logger.warning("Countersign notification failed (non-critical): %s", notif_err)
        finally:
            db.close()

    except TimeoutError:
        logger.warning("Signing timed out for session %d", signing_session_id)
        db = SessionLocal()
        try:
            session = db.query(SigningSession).filter(
                SigningSession.id == signing_session_id
            ).first()
            if session:
                session.status = "expired"
            db.commit()
        finally:
            db.close()

    except Exception as exc:
        logger.error("Signing error for session %d: %s", signing_session_id, exc)
        db = SessionLocal()
        try:
            session = db.query(SigningSession).filter(
                SigningSession.id == signing_session_id
            ).first()
            if session:
                session.status = "error"
            db.commit()
        finally:
            db.close()


async def _notify_incoming_async(document_id: int):
    """Background task to notify the receiver about an incoming document."""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            from app.services.edo_notifications import notify_incoming_document
            await notify_incoming_document(db, doc)
    except Exception as e:
        logger.warning("Incoming document notification failed (non-critical): %s", e)
    finally:
        db.close()

@router.post("/admin/stamp-all-retroactive")
async def stamp_all_retroactive(db: Session = Depends(get_db)):
    """Retroactively stamp all old documents that were signed before stamping was fixed."""
    from app.services.stamp_trigger import maybe_stamp_document
    docs = db.query(Document).filter(Document.edo_status.in_(["signed_both", "signed_self"])).all()
    results = []
    
    for doc in docs:
        if doc.pdf_path:
            try:
                success = await maybe_stamp_document(db, doc.id)
                results.append({"id": doc.id, "success": success})
            except Exception as e:
                results.append({"id": doc.id, "success": False, "error": str(e)})

    return {"processed": len(results), "results": results}


@router.post("/admin/migrate-signatures")
async def migrate_signatures(db: Session = Depends(get_db)):
    """Parse old CMS signatures in DB to extract and populate missing certificate metadata."""
    from app.services.cms_parser import parse_cms_signature
    
    sigs = db.query(Signature).filter(Signature.signature_type == "cms").all()
    results = []
    updated_count = 0
    
    for sig in sigs:
        # Skip if already parsed
        if sig.certificate_serial:
            results.append({"id": sig.id, "status": "skipped"})
            continue
            
        try:
            cert_info = parse_cms_signature(sig.signature_data)
            if cert_info:
                if cert_info.subject_iin: sig.signer_iin = cert_info.subject_iin
                if cert_info.subject_cn: sig.signer_name = cert_info.subject_cn
                if cert_info.subject_org: sig.signer_org_name = cert_info.subject_org
                sig.certificate_serial = cert_info.serial_hex
                if cert_info.valid_from: sig.certificate_valid_from = cert_info.valid_from.replace(tzinfo=None)
                if cert_info.valid_to: sig.certificate_valid_to = cert_info.valid_to.replace(tzinfo=None)
                
                updated_count += 1
                results.append({"id": sig.id, "status": "updated", "serial": cert_info.serial_hex})
            else:
                results.append({"id": sig.id, "status": "error", "reason": "parse failed"})
        except Exception as e:
            results.append({"id": sig.id, "status": "error", "reason": str(e)})

    if updated_count > 0:
        db.commit()
        
    return {"processed": len(results), "updated": updated_count, "results": results}
