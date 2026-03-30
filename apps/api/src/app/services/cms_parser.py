"""
CMS (PKCS#7) Signature Parser — Extracts certificate metadata from Base64 CMS signatures.

Used to populate certificate_serial, certificate_valid_from, certificate_valid_to
and signer identity (IIN, org name) from the ЭЦП signature returned by SIGEX / NCALayer.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CertInfo:
    """Extracted certificate information from CMS signature."""
    serial_hex: str = ""
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    subject_cn: str = ""         # Common Name (ФИО)
    subject_iin: str = ""        # ИИН from serialNumber or OID 2.5.4.5
    subject_org: str = ""        # Organization name
    subject_bin: str = ""        # БИН (from org OID)


def parse_cms_signature(cms_b64: str) -> CertInfo | None:
    """
    Parse a Base64-encoded CMS (PKCS#7) signature and extract the first
    signer's certificate information.
    
    Returns CertInfo or None if parsing fails.
    """
    try:
        from asn1crypto import cms

        raw = base64.b64decode(cms_b64)
        content_info = cms.ContentInfo.load(raw)
        signed_data = content_info["content"]

        # Get certificates embedded in CMS
        certs = signed_data["certificates"]
        if not certs:
            logger.warning("No certificates found in CMS")
            return None

        # Take the first (signer) certificate
        cert = certs[0].chosen  # type: ignore

        # Extract serial number
        serial = cert["tbs_certificate"]["serial_number"].native
        serial_hex = format(serial, "x")

        # Extract validity
        not_before = cert["tbs_certificate"]["validity"]["not_before"].native
        not_after = cert["tbs_certificate"]["validity"]["not_after"].native

        # Extract subject fields
        subject = cert["tbs_certificate"]["subject"]
        import re
        
        cn = ""
        iin = ""
        org = ""
        bin_ = ""
        
        for rdn in subject.chosen:
            for attr in rdn:
                oid = attr["type"].dotted
                value = attr["value"].native
                if not isinstance(value, str):
                    value = str(value)
                
                # Extract IIN and BIN using regex anywhere they appear
                match_iin = re.search(r'IIN(\d{12})', value)
                if match_iin and not iin:
                    iin = match_iin.group(1)
                    
                match_bin = re.search(r'BIN(\d{12})', value)
                if match_bin and not bin_:
                    bin_ = match_bin.group(1)
                
                # Common Name
                if oid == "2.5.4.3":
                    cn = value
                # Serial Number fallback if it contains only 12 digits
                elif oid == "2.5.4.5" and not iin and value.isdigit() and len(value) == 12:
                    iin = value
                # Organization
                elif oid == "2.5.4.10":
                    org = value

        # Convert datetimes
        valid_from = not_before if isinstance(not_before, datetime) else None
        valid_to = not_after if isinstance(not_after, datetime) else None

        info = CertInfo(
            serial_hex=serial_hex,
            valid_from=valid_from,
            valid_to=valid_to,
            subject_cn=cn,
            subject_iin=iin,
            subject_org=org,
            subject_bin=bin_,
        )

        logger.info("CMS parsed: CN=%s, IIN=%s, serial=%s", cn, iin, serial_hex[:16])
        return info

    except Exception as exc:
        logger.error("Failed to parse CMS signature: %s", exc)
        return None
