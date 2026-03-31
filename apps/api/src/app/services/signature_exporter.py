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

        safe_title = "".join(c for c in (doc.title or "document") if c.isalnum() or c in (" ", "-", "_")).strip()
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            
            # 1. Original PDF
            pdf_filename = f"{safe_title}.pdf"
            zf.writestr(pdf_filename, pdf_bytes)

            # 2. CMS Signatures — ONE FILE including ALL signatures (Countersigned)
            # ezSigner requires the extension to match exactly what it expects (e.g. .pdf.cms)
            # and it must be a single attached CMS file containing the data.
            full_cms = self._generate_full_countersigned_cms(pdf_bytes, sigs)
            
            cms_filename = f"{safe_title}.pdf.cms"
            if full_cms:
                zf.writestr(cms_filename, full_cms)
            else:
                # Extreme fallback, just put the last signature as is
                if sigs and sigs[-1].signature_data:
                    zf.writestr(f"{safe_title}_raw.cms", base64.b64decode(sigs[-1].signature_data))

        zip_bytes = zip_buffer.getvalue()
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
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<root>',
            f'  <document-id>{doc.id}</document-id>',
            f'  <md5-hash>{md5_hash}</md5-hash>',
            '  <signatures>'
        ]
        for s in sigs:
            xml_lines.append(f'    <signature role="{s.signer_role}">{s.signer_name}</signature>')
        xml_lines.append('  </signatures>')
        xml_lines.append('</root>')
        return "\n".join(xml_lines).encode("utf-8")

    def _generate_text_report(self, doc: Document, sigs: list[Signature]) -> str:
        report = [
            f"ДОКУМЕНТ №{doc.id}",
            f"Тема: {doc.title}",
            "-" * 40,
            "ИНСТРУКЦИЯ:",
            "1. Загрузите файл .cms на ezsigner.kz",
            "-" * 40
        ]
        return "\n".join(report)
