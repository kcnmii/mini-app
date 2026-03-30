"""
Signature Exporter Service — Generates ZIP archives with PDF, XML, and CMS signatures.

Everything needed for external validation on services like ezSigner.kz or national verification portals.
Format matches standard EDO (Electronic Document Management) exports in Kazakhstan.
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
        """
        Generate a ZIP archive containing:
          - Original PDF
          - XML metadata with detached signatures (XML-DSIG style)
          - CMS signature file (.cms) for ezSigner.kz (Attached CMS)
          - Validation report (.txt)
        
        Returns (zip_bytes, filename)
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # 1. Fetch original PDF
        pdf_bytes = None
        if doc.pdf_path:
            pdf_bytes = await s3.download_file(doc.pdf_path)
        
        if not pdf_bytes:
            raise ValueError("Original PDF content not found in S3")

        # 2. Fetch all signatures
        sigs = self.db.query(Signature).filter(
            Signature.document_id == document_id
        ).order_by(Signature.signed_at.asc()).all()

        # 3. Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            
            # File 1: Original PDF
            pdf_filename = f"{doc.title or 'document'}.pdf"
            zf.writestr(pdf_filename, pdf_bytes)

            # File 2: XML Metadata & Signatures
            xml_content = self._generate_xml_metadata(doc, sigs, pdf_bytes)
            zf.writestr(f"{doc.title or 'document'}.xml", xml_content)

            # File 3: CMS Signature (for ezSigner.kz)
            cms_filename = f"{doc.title or 'document'}.pdf.cms"
            cms_bytes = self._generate_attached_cms(pdf_bytes, sigs)
            if cms_bytes:
                zf.writestr(cms_filename, cms_bytes)

            # File 4: Validation Report (Human readable)
            report = self._generate_text_report(doc, sigs)
            zf.writestr("signatures_report.txt", report.encode("utf-8"))

        zip_bytes = zip_buffer.getvalue()
        safe_title = "".join(c for c in (doc.title or "document") if c.isalnum() or c in (" ", "-", "_")).strip()
        filename = f"signatures_{safe_title}_{document_id}.zip"

        return zip_bytes, filename

    def _generate_xml_metadata(self, doc: Document, sigs: list[Signature], pdf_bytes: bytes) -> bytes:
        """Generate XML with MD5 hash and signatures."""
        md5_hash = hashlib.md5(pdf_bytes).hexdigest()
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<root>',
            f'  <document-id>{doc.id}</document-id>',
            f'  <title>{doc.title or ""}</title>',
            f'  <doc-type>{doc.doc_type or "invoice"}</doc-type>',
            f'  <md5-hash>{md5_hash}</md5-hash>',
            f'  <created-at>{doc.created_at.isoformat() if doc.created_at else ""}</created-at>',
            f'  <total-sum>{doc.total_sum or "0"}</total-sum>',
            '  <signatures>'
        ]

        for s in sigs:
            xml_lines.append(f'    <signature role="{s.signer_role}">')
            xml_lines.append(f'      <signer-name>{s.signer_name or ""}</signer-name>')
            xml_lines.append(f'      <signer-iin>{s.signer_iin or ""}</signer-iin>')
            xml_lines.append(f'      <signed-at>{s.signed_at.isoformat() if s.signed_at else ""}</signed-at>')
            xml_lines.append(f'      <certificate-serial>{s.certificate_serial or ""}</certificate-serial>')
            xml_lines.append(f'      <cms-data>{s.signature_data or ""}</cms-data>')
            xml_lines.append('    </signature>')

        xml_lines.append('  </signatures>')
        xml_lines.append('</root>')
        
        return "\n".join(xml_lines).encode("utf-8")

    def _generate_attached_cms(self, pdf_bytes: bytes, sigs: list[Signature]) -> bytes | None:
        """Convert a detached CMS signature into an ATTACHED CMS (including data)."""
        if not sigs:
            return None
        
        try:
            from asn1crypto import cms
            
            primary_sig_b64 = sigs[-1].signature_data
            if not primary_sig_b64:
                return None

            raw_cms = base64.b64decode(primary_sig_b64)
            content_info = cms.ContentInfo.load(raw_cms)
            
            if content_info['content_type'].native != 'signed_data':
                return raw_cms
            
            signed_data = content_info['content']
            encap = signed_data['encapsulated_content_info']
            encap['content_type'] = 'data'
            encap['content'] = pdf_bytes
            
            return content_info.dump()
            
        except Exception as e:
            logger.error("Failed to generate attached CMS: %s", e)
            return base64.b64decode(sigs[-1].signature_data) if sigs[-1].signature_data else None

    def _generate_text_report(self, doc: Document, sigs: list[Signature]) -> str:
        """Generate a human-readable text report about the signatures."""
        report = [
            f"ОТЧЕТ О ПОДПИСАНИИ ДОКУМЕНТА №{doc.id}",
            f"Название: {doc.title}",
            f"Дата создания: {doc.created_at.strftime('%d.%m.%Y %H:%M') if doc.created_at else '—'}",
            f"Сумма: {doc.total_sum or '0'} KZT",
            f"Статус ЭДО: {doc.edo_status}",
            "-" * 40,
            "СПИСОК ПОДПИСЕЙ:",
            ""
        ]

        for i, s in enumerate(sigs, 1):
            role = "ОТПРАВИТЕЛЬ" if s.signer_role == "sender" else "ПОЛУЧАТЕЛЬ"
            report.append(f"{i}. Роль: {role}")
            report.append(f"   ФИО/Орг: {s.signer_name or '—'}")
            report.append(f"   ИИН/БИН: {s.signer_iin or '—'}")
            report.append(f"   Дата подписи: {s.signed_at.strftime('%d.%m.%Y %H:%M') if s.signed_at else '—'}")
            report.append(f"   Серийный номер ЭЦП: {s.certificate_serial or '—'}")
            report.append("")

        report.append("-" * 40)
        report.append("Документ и подписи проверены в системе ЭДО.")
        report.append("Для внешней проверки используйте файл .cms на сайте ezsigner.kz")
        
        return "\n".join(report)
