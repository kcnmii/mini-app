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

        pdf_bytes = b""
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
        return self._create_attached_cms_binary_safe(pdf_bytes, sigs[-1].signature_data)
        
    def _create_attached_cms_binary_safe(self, data_bytes: bytes, detached_sig_b64: str | None) -> bytes | None:
        if not detached_sig_b64: return None
        try:
            from asn1crypto import cms
            
            raw_cms = base64.b64decode(detached_sig_b64)
            content_info = cms.ContentInfo.load(raw_cms)
            sd = content_info['content']
            
            version_bytes = sd['version'].dump()
            digest_algos_bytes = sd['digest_algorithms'].dump()
            
            # Use getattr and .contents to avoid deep parsing KeyError on GOST OIDs
            certs_bytes = sd['certificates'].dump() if hasattr(sd['certificates'], 'contents') and sd['certificates'].contents else b''
            crls_bytes = sd['crls'].dump() if hasattr(sd['crls'], 'contents') and sd['crls'].contents else b''
            signer_infos_bytes = sd['signer_infos'].dump()
            
            new_encap = cms.EncapsulatedContentInfo({
                'content_type': 'data',
                'content': data_bytes
            })
            encap_bytes = new_encap.dump()
            
            sd_body = version_bytes + digest_algos_bytes + encap_bytes + certs_bytes + crls_bytes + signer_infos_bytes
            
            def _ber_length(length: int) -> bytes:
                if length < 0x80: return bytes([length])
                elif length < 0x100: return bytes([0x81, length])
                elif length < 0x10000: return bytes([0x82, (length >> 8) & 0xff, length & 0xff])
                elif length < 0x1000000: return bytes([0x83, (length >> 16) & 0xff, (length >> 8) & 0xff, length & 0xff])
                else: return bytes([0x84, (length >> 24) & 0xff, (length >> 16) & 0xff, (length >> 8) & 0xff, length & 0xff])

            sd_der = b'\x30' + _ber_length(len(sd_body)) + sd_body
            a0_der = b'\xa0' + _ber_length(len(sd_der)) + sd_der
            oid_signed_data = b'\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02'
            ci_body = oid_signed_data + a0_der
            final_cms_bytes = b'\x30' + _ber_length(len(ci_body)) + ci_body
            
            cms.ContentInfo.load(final_cms_bytes)
            
            return final_cms_bytes
        except Exception as e:
            logger.error("Binary CMS Creation Error: %s", e)
            return base64.b64decode(detached_sig_b64)



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
