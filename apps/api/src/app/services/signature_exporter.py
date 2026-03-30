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
            
            # 1. Original PDF
            pdf_filename = f"{doc.title or 'document'}.pdf"
            zf.writestr(pdf_filename, pdf_bytes)

            # 2. XML Metadata & Signatures
            xml_content = self._generate_xml_metadata(doc, sigs, pdf_bytes)
            zf.writestr(f"{doc.title or 'document'}.xml", xml_content)

            # 3. ATTACHED CMS (including data)
            # This is what ezSigner.kz expects for one-file verification
            for i, s in enumerate(sigs):
                role_suffix = "sender" if s.signer_role == "sender" else "receiver"
                cms_filename = f"signature_{i+1}_{role_suffix}_WITH_DATA.cms"
                attached_cms = self._create_attached_cms(pdf_bytes, s.signature_data)
                if attached_cms:
                    zf.writestr(cms_filename, attached_cms)

            # 4. Validation Report
            report = self._generate_text_report(doc, sigs)
            zf.writestr("signatures_report.txt", report.encode("utf-8"))

        zip_bytes = zip_buffer.getvalue()
        safe_title = "".join(c for c in (doc.title or "document") if c.isalnum() or c in (" ", "-", "_")).strip()
        filename = f"signatures_{safe_title}_{document_id}.zip"

        return zip_bytes, filename

    def _create_attached_cms(self, data_bytes: bytes, detached_sig_b64: str | None) -> bytes | None:
        """
        Manually construct an Attached CMS from Detached signature data.
        Injects the original data bytes into the ContentInfo structure.
        """
        if not detached_sig_b64:
            return None
        
        try:
            from asn1crypto import cms
            
            raw_cms = base64.b64decode(detached_sig_b64)
            content_info = cms.ContentInfo.load(raw_cms)
            
            if content_info['content_type'].native != 'signed_data':
                return raw_cms
            
            # Create a copy and inject the content
            signed_data = content_info['content']
            
            # Set the actual data content
            signed_data['encapsulated_content_info']['content_type'] = 'data'
            signed_data['encapsulated_content_info']['content'] = data_bytes
            
            return content_info.dump()
        except Exception as e:
            logger.error("Failed to inject data into CMS: %s", e)
            return base64.b64decode(detached_sig_b64)

    def _generate_xml_metadata(self, doc: Document, sigs: list[Signature], pdf_bytes: bytes) -> bytes:
        md5_hash = hashlib.md5(pdf_bytes).hexdigest()
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<root>',
            f'  <document-id>{doc.id}</document-id>',
            f'  <title>{doc.title or ""}</title>',
            f'  <md5-hash>{md5_hash}</md5-hash>',
            '  <signatures>'
        ]

        for s in sigs:
            xml_lines.append(f'    <signature role="{s.signer_role}">')
            xml_lines.append(f'      <signer-name>{s.signer_name or ""}</signer-name>')
            xml_lines.append(f'      <signer-iin>{s.signer_iin or ""}</signer-iin>')
            xml_lines.append(f'      <signed-at>{s.signed_at.isoformat() if s.signed_at else ""}</signed-at>')
            xml_lines.append('    </signature>')

        xml_lines.append('  </signatures>')
        xml_lines.append('</root>')
        
        return "\n".join(xml_lines).encode("utf-8")

    def _generate_text_report(self, doc: Document, sigs: list[Signature]) -> str:
        report = [
            f"ОТЧЕТ О ПОДПИСАНИИ ДОКУМЕНТА №{doc.id}",
            f"Название: {doc.title}",
            "-" * 40,
            "ИНСТРУКЦИЯ ДЛЯ EZSIGNER.KZ:",
            "1. Зайдите на https://ezsigner.kz/#!/main",
            "2. Выберите раздел 'Проверить документ'",
            "3. Загрузите в поле только ОДИН файл из архива (файл с расширением .cms)",
            "4. Система сама извлечет документ и проверит подписи.",
            "-" * 40,
            "СПИСОК ПОДПИСЕЙ:",
            ""
        ]

        for i, s in enumerate(sigs, 1):
            report.append(f"{i}. {s.signer_name or '—'} (ИИН: {s.signer_iin or '—'})")
            report.append(f"   Дата: {s.signed_at.strftime('%d.%m.%Y %H:%M') if s.signed_at else '—'}")
            report.append("")

        return "\n".join(report)
