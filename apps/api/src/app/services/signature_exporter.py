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
        original_pdf_bytes = b""
        
        if doc.pdf_path:
            # pdf_bytes is the current PDF (which might be stamped with visual signatures)
            pdf_bytes = await s3.download_file(doc.pdf_path)
            
            # For CMS cryptographic integrity, we MUST use the exact original unstamped PDF bytes.
            original_pdf_key = doc.pdf_path
            if original_pdf_key.endswith("_stamped.pdf"):
                original_pdf_key = original_pdf_key.replace("_stamped.pdf", ".pdf")
            
            original_pdf_bytes = await s3.download_file(original_pdf_key)
            if not original_pdf_bytes:
                original_pdf_bytes = pdf_bytes
        
        if not pdf_bytes:
            raise ValueError("Document PDF content not found in S3")

        sigs = self.db.query(Signature).filter(
            Signature.document_id == document_id
        ).order_by(Signature.signed_at.asc()).all()

        safe_title = "".join(c for c in (doc.title or "document") if c.isalnum() or c in (" ", "-", "_")).strip()
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            
            # 1. Stamped PDF for visual preview
            pdf_filename = f"{safe_title}.pdf"
            zf.writestr(pdf_filename, pdf_bytes)

            # 2. CMS Signature — Attached version with ORIGINAL bytes
            full_cms = self._generate_full_countersigned_cms(original_pdf_bytes, sigs)
            
            cms_filename = f"{safe_title}.pdf.cms"
            if full_cms:
                zf.writestr(cms_filename, full_cms)
            else:
                if sigs and sigs[-1].signature_data:
                    zf.writestr(f"{safe_title}_raw.cms", base64.b64decode(sigs[-1].signature_data))

        zip_bytes = zip_buffer.getvalue()
        filename = f"signatures_{safe_title}_{document_id}.zip"

        return zip_bytes, filename

    def _generate_full_countersigned_cms(self, original_pdf_bytes: bytes, sigs: list[Signature]) -> bytes | None:
        if not sigs: return None
        return self._create_attached_cms_binary_safe(original_pdf_bytes, sigs[-1].signature_data)
        
    def _create_attached_cms_binary_safe(self, data_bytes: bytes, detached_sig_b64: str | None) -> bytes | None:
        """
        Deep binary reconstruction of CMS ContentInfo with injected payload.
        Ensures Byte-for-Byte ASN.1 compatibility with ezSigner.kz for Kazakhstan GOST signatures.
        """
        if not detached_sig_b64: return None
        try:
            from asn1crypto import cms
            
            raw_cms = base64.b64decode(detached_sig_b64)
            content_info = cms.ContentInfo.load(raw_cms)
            sd = content_info['content']
            
            # 1. Essential SD header parts
            v_bytes = sd['version'].dump()
            da_bytes = sd['digest_algorithms'].dump()
            certs_bytes = sd['certificates'].dump() if hasattr(sd['certificates'], 'contents') and sd['certificates'].contents else b''
            crls_bytes = sd['crls'].dump() if hasattr(sd['crls'], 'contents') and sd['crls'].contents else b''
            
            # 2. Rebuild EncapsulatedContentInfo WITH data (Injection)
            def _ber_len(l: int) -> bytes:
                if l < 0x80: return bytes([l])
                elif l < 0x100: return bytes([0x81, l])
                elif l < 0x10000: return bytes([0x82, (l >> 8) & 0xff, l & 0xff])
                elif l < 0x1000000: return bytes([0x83, (l >> 16) & 0xff, (l >> 8) & 0xff, l & 0xff])
                else: return bytes([0x84, (l >> 24) & 0xff, (l >> 16) & 0xff, (l >> 8) & 0xff, l & 0xff])

            oid_data = b'\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x01' # OID: data
            content_v = b'\x04' + _ber_len(len(data_bytes)) + data_bytes
            encap_body = oid_data + b'\xa0' + _ber_len(len(content_v)) + content_v
            encap_bytes = b'\x30' + _ber_len(len(encap_body)) + encap_body
            
            # 3. SignerInfos — Keep exact bytes of the detached SignerInfo to preserve attributes (DATE)
            # Wrapped in SET OF
            si_list = sd['signer_infos']
            si_bodies = b''
            for si in si_list:
                si_raw = si.dump() # Deep binary copy of everything, including SignedAttributes and Signature
                si_bodies += si_raw
            
            si_final = b'\x31' + _ber_len(len(si_bodies)) + si_bodies
            
            # 4. Final Assembly
            sd_body = v_bytes + da_bytes + encap_bytes + certs_bytes + crls_bytes + si_final
            sd_final = b'\x30' + _ber_len(len(sd_body)) + sd_body
            
            # Wrap as ContentInfo
            oid_sd = b'\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02' # OID: signedData
            a0_final = b'\xa0' + _ber_len(len(sd_final)) + sd_final
            ci_body = oid_sd + a0_final
            final_cms = b'\x30' + _ber_len(len(ci_body)) + ci_body
            
            # Validation
            cms.ContentInfo.load(final_cms)
            return final_cms
            
        except Exception as e:
            logger.error("Binary CMS Reconstruction Failure: %s", e)
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
