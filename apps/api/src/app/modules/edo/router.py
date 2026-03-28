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

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
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
    request: Request,
    req: SignDocumentRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Start the ЭЦП signing process for a document.
    
    1. Loads document PDF from S3
    2. Registers signing procedure with SIGEX
    3. Returns eGov Mobile deeplink for the user to sign
    4. Starts background polling for signature
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
    md5_hash = hashlib.md5(pdf_bytes).hexdigest()
    doc.md5_hash = md5_hash

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

    try:
        result = await sigex.initiate_signing(
            document_bytes=pdf_bytes,
            description=f"Подписание: {doc.title}",
            names=[doc.title, doc.title, doc.title],
            meta=meta,
        )
    except Exception as exc:
        logger.error("SIGEX initiate_signing failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Ошибка SIGEX: {exc}") from exc

    # Save signing session
    session = SigningSession(
        document_id=doc.id,
        user_id=user_id,
        sign_url=result["sign_url"],
        egov_mobile_link=result["eGovMobileLaunchLink"],
        egov_business_link=result["eGovBusinessLaunchLink"],
        qr_code_b64=result["qr_code_b64"],
        status="pending",
        signer_role=req.signer_role,
    )
    db.add(session)

    # Update document status
    doc.edo_status = "awaiting_sign"
    db.commit()
    db.refresh(session)

    # Start background polling for signature
    background_tasks.add_task(
        _poll_and_save_signature,
        signing_session_id=session.id,
        sign_url=result["sign_url"],
        document_id=doc.id,
        user_id=user_id,
        signer_iin=signer_iin,
        signer_name=signer_name,
        signer_role=req.signer_role,
    )

    # 🚀 Iron-clad iOS Fallback: Send deep link to the Telegram Chat! 🚀
    if result.get("eGovMobileLaunchLink"):
        try:
            import urllib.parse
            from app.modules.telegram_bot.service import TelegramBotClient
            bot = TelegramBotClient()
            
            # Telegram strictly blocks non-HTTP URLs in inline buttons.
            # We must use our own endpoint to bounce the user to the custom scheme.
            safe_url = urllib.parse.quote(result["eGovMobileLaunchLink"])
            base_url = str(request.base_url).rstrip("/")
            
            # The bounce URL inside our API
            redirect_url = f"{base_url}/edo/mobile-redirect?url={safe_url}"

            await bot.send_egov_signing_link(
                chat_id=user_id,
                text=f"Нажмите кнопку ниже, чтобы перейти в <b>eGov Mobile</b> и подписать документ:\n\n📄 <b>{doc.title}</b>",
                egov_link=redirect_url,
            )
            await bot.close()
        except Exception as e:
            logger.warning("Failed to send eGov link to telegram: %s", e)

    return SignDocumentResponse(
        signing_session_id=session.id,
        egov_mobile_link=result["eGovMobileLaunchLink"],
        egov_business_link=result["eGovBusinessLaunchLink"],
        qr_code_b64=result["qr_code_b64"],
    )


# ──────────────────────────────────────────────
# GET /edo/mobile-redirect - Bounce to custom scheme
# ──────────────────────────────────────────────
@router.get("/mobile-redirect")
async def mobile_redirect(url: str):
    """
    Bounces HTTP requests from Telegram inline buttons to custom schemes.
    (Telegram restricts inline buttons to valid http/https URLs).
    """
    return RedirectResponse(url)


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
# POST /edo/share — Share document with counterparty
# ──────────────────────────────────────────────
@router.post("/share", response_model=ShareDocumentResponse)
async def share_document(
    req: ShareDocumentRequest,
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

        # Save to DB
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            sig = Signature(
                document_id=document_id,
                signer_iin=signer_iin,
                signer_name=signer_name,
                signer_role=signer_role,
                signature_data=cms_signature_b64,
                signature_type="cms",
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
                "Signature saved for document %d, signer=%s, role=%s",
                document_id, signer_name, signer_role,
            )
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
