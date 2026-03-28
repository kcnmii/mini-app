"""
Utility to apply ЭДО stamp to a document when both parties have signed.

Call `maybe_stamp_document(db, document_id)` after saving a signature.
If both sender and receiver have signed, the PDF is stamped with header + footer.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from app.core.db import Document, Signature, SupplierProfile
from app.services.pdf_stamper import StampConfig, SignerInfo, stamp_document_pdf

logger = logging.getLogger(__name__)


async def maybe_stamp_document(db: Session, document_id: int, base_url: str = "https://api.doc.onlink.kz") -> bool:
    """
    Check if document has both sender and receiver signatures.
    If yes, apply the ЭДО stamp to the PDF (via S3).
    Returns True if stamp was applied, False otherwise.
    """
    from app.core import s3

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not doc.pdf_path:
        return "No doc or pdf_path"

    # Get all signatures
    sigs = db.query(Signature).filter(Signature.document_id == document_id).all()
    sender_sig = next((s for s in sigs if s.signer_role == "sender"), None)
    receiver_sig = next((s for s in sigs if s.signer_role == "receiver"), None)

    if not sender_sig and not receiver_sig:
        return "No signatures found in DB"

    # Get sender profile for org info
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.user_id == doc.user_id
    ).first()

    # Build stamp config
    from app.core.db import DocumentShare
    share = db.query(DocumentShare).filter(
        DocumentShare.document_id == document_id,
    ).first()
    share_uuid = share.share_uuid if share else ""

    doc_url = f"{base_url}/edo/doc/{share_uuid}" if share_uuid else ""

    sender_info = None
    if sender_sig:
        sender_info = SignerInfo(
            role="sender",
            role_label="Отправитель",
            org_name=(profile.company_name if profile else "") or "",
            org_bin=(profile.company_iin if profile else "") or "",
            full_name=sender_sig.signer_name or "",
            cert_serial=sender_sig.certificate_serial or "",
            cert_valid_from=sender_sig.certificate_valid_from.strftime("%Y-%m-%dT%H:%M:%S") if sender_sig.certificate_valid_from else "",
            cert_valid_to=sender_sig.certificate_valid_to.strftime("%Y-%m-%dT%H:%M:%S") if sender_sig.certificate_valid_to else "",
            signed_at=sender_sig.signed_at.strftime("%Y-%m-%d %H:%M") if sender_sig.signed_at else "",
            signer_title="Первый руководитель",
        )

    receiver_info = None
    if receiver_sig:
        receiver_info = SignerInfo(
            role="receiver",
            role_label="Получатель",
            org_name=receiver_sig.signer_org_name or "",
            org_bin="",
            full_name=receiver_sig.signer_name or "",
            cert_serial=receiver_sig.certificate_serial or "",
            cert_valid_from=receiver_sig.certificate_valid_from.strftime("%Y-%m-%dT%H:%M:%S") if receiver_sig.certificate_valid_from else "",
            cert_valid_to=receiver_sig.certificate_valid_to.strftime("%Y-%m-%dT%H:%M:%S") if receiver_sig.certificate_valid_to else "",
            signed_at=receiver_sig.signed_at.strftime("%Y-%m-%d %H:%M") if receiver_sig.signed_at else "",
            signer_title="ИП (личный ключ)",
        )

    config = StampConfig(
        doc_url=doc_url,
        md5_hash=doc.md5_hash or "",
        edo_service_name="ЭДО Doc App",
        edo_service_url="https://doc.onlink.kz",
        sender=sender_info,
        receiver=receiver_info,
    )

    # ALWAYS fetch the original, unstamped PDF to prevent double-stamping
    original_pdf_key = doc.pdf_path
    if original_pdf_key.endswith("_stamped.pdf"):
        original_pdf_key = original_pdf_key.replace("_stamped.pdf", ".pdf")

    try:
        pdf_bytes = await s3.download_file(original_pdf_key)
        if not pdf_bytes:
            logger.warning("Original PDF not found in S3 for stamping: %s", original_pdf_key)
            return f"Original PDF not found in S3: {original_pdf_key}"

        # Add stamp in memory
        from app.services.pdf_stamper import add_stamp_to_pdf
        stamped_bytes = add_stamp_to_pdf(pdf_bytes, config)

        # Upload stamped version
        stamped_key = original_pdf_key.replace(".pdf", "_stamped.pdf")
        await s3.upload_file(stamped_key, stamped_bytes)

        # Update document to point to stamped version
        doc.pdf_path = stamped_key
        # Update edo_status only if it transitioned fully
        if sender_sig and receiver_sig:
            doc.edo_status = "signed_both"
        elif sender_sig:
            doc.edo_status = "signed_self"
        db.commit()

        logger.info("Document %d stamped successfully (S3): %s", document_id, stamped_key)
        return True

    except Exception as exc:
        logger.error("Failed to stamp document %d: %s", document_id, exc)
        return False
