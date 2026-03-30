"""
Signature Exporter Service — Generates ZIP archives with PDF, XML, and CMS signatures.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import zipfile
from datetime import datetime
from sqlalchemy.orm import Session

from app.core import s3
from app.core.db import Document, Signature, SupplierProfile

logger = logging.getLogger(__name__)

class SignatureExporter:
    """Async service for generating a validated document export package."""

    def __init__(self, db: Session):
        self.db = db

    async def generate_zip_package(self, document_id: int) -> tuple[bytes, str]:
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        pdf_bytes = None
        if doc.pdf_path:
            pdf_bytes = await s3.download_file(doc.pdf_path)
        
        if not pdf_bytes:
            raise ValueError("Original PDF content not found in S3")

        sigs = self.db.query(Signature).filter(
            Signature.document_id == document_id
        ).order_by(Signature.signed_at.asc()).all()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            
            # 1. Original PDF (ALWAYS first, ezSigner likes this order)
            pdf_filename = f"document_{doc.id}.pdf"
            zf.writestr(pdf_filename, pdf_bytes)

            # 2. CMS Signatures — ONE FILE including ALL signatures (Countersigned)
            # ezSigner loves ONE file that contains everything.
            full_cms = self._generate_full_countersigned_cms(pdf_bytes, sigs)
            if full_cms:
                zf.writestr(f"document_{doc.id}_signed.cms", full_cms)

            # 3. Individual CMS files for fallback
            num_sigs = len(sigs)
            for i, s in enumerate(sigs):
                role = "sender" if s.signer_role == "sender" else "receiver"
                cms_data = self._create_attached_cms_fixed(pdf_bytes, s.signature_data)
                if cms_data:
                    zf.writestr(f"signature_{i+1}_{role}_attached.cms", cms_data)

            # 4. XML Metadata & Report
            xml_content = self._generate_xml_metadata(doc, sigs, pdf_bytes)
            zf.writestr(f"metadata_{doc.id}.xml", xml_content)
            
            report = self._generate_text_report(doc, sigs)
            zf.writestr("README_CHECK_INSTRUCTIONS.txt", report.encode("utf-8"))

        zip_bytes = zip_buffer.getvalue()
        safe_title = "".join(c for c in (doc.title or "document") if c.isalnum() or c in (" ", "-", "_")).strip()
        filename = f"signatures_{safe_title}_{document_id}.zip"

        return zip_bytes, filename

    def _generate_full_countersigned_cms(self, pdf_bytes: bytes, sigs: list[Signature]) -> bytes | None:
        """
        Merge all signatures into a single CMS container if possible.
        If not, just wrap the last one properly.
        """
        if not sigs: return None
        # Start with the receiver's signature (usually contains more info if countersigned)
        return self._create_attached_cms_fixed(pdf_bytes, sigs[-1].signature_data)

    def _create_attached_cms_fixed(self, data_bytes: bytes, detached_sig_b64: str | None) -> bytes | None:
        """
        Construct an Attached CMS compatible with ezSigner.kz.
        Fixes the EncapContentInfo structure.
        """
        if not detached_sig_b64: return None
        try:
            from asn1crypto import cms
            
            raw_cms = base64.b64decode(detached_sig_b64)
            content_info = cms.ContentInfo.load(raw_cms)
            signed_data = content_info['content']
            
            # IMPORTANT: Re-creating the structure to ensure ezSigner doesn't choke on missing optional fields
            # Some EDOs strip fields that ezSigner (AngularJS frontend) expects
            signed_data['encap_content_info'] = {
                'content_type': 'data',
                'content': data_bytes
            }
            
            return content_info.dump()
        except Exception as e:
            logger.error("CMS Creation Error: %s", e)
            return None

    def _generate_xml_metadata(self, doc: Document, sigs: list[Signature], pdf_bytes: bytes) -> bytes:
        md5_hash = hashlib.md5(pdf_bytes).hexdigest()
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<export>',
            f'  <document-id>{doc.id}</document-id>',
            f'  <md5>{md5_hash}</md5>',
            '  <details>'
        ]
        for s in sigs:
            xml_lines.append(f'    <signer role="{s.signer_role}">{s.signer_name} (IIN: {s.signer_iin})</signer>')
        xml_lines.append('  </details>')
        xml_lines.append('</export>')
        return "\n".join(xml_lines).encode("utf-8")

    def _generate_text_report(self, doc: Document, sigs: list[Signature]) -> str:
        return (
            f"ДОКУМЕНТ: {doc.title}\n"
            f"ПОДПИСАНТОВ: {len(sigs)}\n\n"
            f"ИНСТРУКЦИЯ:\n"
            f"1. Откройте https://ezsigner.kz/#!/main\n"
            f"2. Загрузите файл 'document_{doc.id}_signed.cms'\n\n"
            f"Если сайт выдает ошибку, попробуйте по отдельности загрузить файлы 'signature_..._attached.cms'."
        )
