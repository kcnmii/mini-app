"""
PDF Stamp Service — Adds ЭДО header and signature footer to PDF documents.

Uses PyMuPDF (fitz) to draw directly on existing PDFs.

Header (top of first page):
  - "Документ зарегистрирован и подписан с помощью сервиса ЭДО"
  - MD5 Hash, Links for sender/receiver

Footer (bottom of last page):
  - Signature table with sender and receiver data
  - QR codes linking to the document page
"""

from __future__ import annotations

import base64
import io
import logging
import os
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import qrcode
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


@dataclass
class SignerInfo:
    """Info about a signer to render in the stamp."""
    role: str = "sender"  # sender | receiver
    role_label: str = "Отправитель"
    org_name: str = ""
    org_bin: str = ""
    full_name: str = ""
    cert_serial: str = ""
    cert_valid_from: str = ""
    cert_valid_to: str = ""
    signed_at: str = ""
    signer_title: str = ""  # e.g. "Первый руководитель"


@dataclass
class StampConfig:
    """Configuration for the PDF stamp."""
    doc_url: str = ""
    md5_hash: str = ""
    sender: SignerInfo | None = None
    receiver: SignerInfo | None = None
    edo_service_name: str = "ЭДО Doc App"
    edo_service_url: str = "https://doc.onlink.kz"


def add_stamp_to_pdf(
    pdf_bytes: bytes,
    config: StampConfig,
) -> bytes:
    """
    Add a header (top of first page) and a signature footer (bottom of last page)
    to an existing PDF. Returns the stamped PDF bytes.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        # ── Add header to first page ──
        if doc.page_count > 0:
            _add_header(doc[0], config)

        # ── Add footer to last page ──
        if doc.page_count > 0 and (config.sender or config.receiver):
            _add_footer(doc[-1], config)

        # Save to bytes
        output = doc.tobytes(deflate=True, garbage=4)
    finally:
        doc.close()

    return output


def _add_header(page: fitz.Page, config: StampConfig):
    """Draw a premium ЭДО header at the top of the first page."""
    width = page.rect.width
    header_height = 55
    margin = 35
    
    # Text colors
    PRIMARY_BLUE = (0.016, 0.231, 0.455)  # #043B74
    TEXT_GRAY = (0.4, 0.4, 0.5)
    
    # Extend page box for header
    original_rect = page.rect
    page.set_mediabox(fitz.Rect(0, -header_height, original_rect.width, original_rect.height))

    # Background
    header_rect = fitz.Rect(margin, -header_height + 10, width - margin, -10)
    page.draw_rect(header_rect, color=None, fill=(0.97, 0.98, 1.0))
    
    # Border
    page.draw_line(fitz.Point(margin, -10), fitz.Point(width - margin, -10), color=(0.9, 0.9, 0.94), width=0.5)

    y = -header_height + 25
    
    # Main Header Text
    page.insert_text(
        fitz.Point(margin + 5, y),
        "ДОКУМЕНТ ЗАРЕГИСТРИРОВАН И ПОДПИСАН В СИСТЕМЕ ЭДО doc.onlink.kz",
        fontsize=8.5,
        fontname="helv",
        color=PRIMARY_BLUE,
    )
    
    y += 12
    # MD5 Hash text
    if config.md5_hash:
        page.insert_text(
            fitz.Point(margin + 5, y),
            f"MD5 Hash документа: {config.md5_hash}",
            fontsize=7,
            fontname="helv",
            color=TEXT_GRAY,
        )

    # Verification URL at far right
    if config.doc_url:
        page.insert_text(
            fitz.Point(width - margin - 150, y - 6),
            "Проверить подлинность:",
            fontsize=6,
            fontname="helv",
            color=TEXT_GRAY,
        )
        page.insert_text(
            fitz.Point(width - margin - 150, y + 2),
            config.doc_url,
            fontsize=6.5,
            fontname="helv",
            color=PRIMARY_BLUE,
        )


def _add_footer(page: fitz.Page, config: StampConfig):
    """Draw a professional signature table (Uchet style) at the bottom."""
    width = page.rect.width
    margin = 35
    footer_height = 200
    
    # Style constants
    PRIMARY_BLUE = (0.016, 0.231, 0.455)  # #043B74
    BORDER_GRAY = (0.85, 0.85, 0.88)
    LABEL_COLOR = (0.45, 0.45, 0.5)
    VALUE_COLOR = (0.1, 0.1, 0.15)
    
    # Extend page downward
    original_rect = page.rect
    page.set_mediabox(fitz.Rect(0, 0, original_rect.width, original_rect.height + footer_height))
    
    footer_top = original_rect.height + 15
    box_width = (width - 2 * margin - 20) / 2
    
    # Helper to draw a signer box
    def draw_signer_box(x, y, signer: SignerInfo | None, is_sender: bool):
        box_rect = fitz.Rect(x, y, x + box_width, y + 175)
        # Background box
        page.draw_rect(box_rect, color=BORDER_GRAY, width=0.5, fill=(0.99, 0.99, 1.0))
        
        y_text = y + 15
        role_label = "ОТПРАВИТЕЛЬ" if is_sender else "ПОЛУЧАТЕЛЬ"
        
        # Header of the box
        page.insert_text(fitz.Point(x + 10, y_text), role_label, fontsize=7.5, fontname="helv", color=PRIMARY_BLUE)
        
        if not signer:
            page.insert_text(fitz.Point(x + 10, y_text + 40), "ОЖИДАНИЕ ПОДПИСИ", fontsize=9, fontname="helv", color=(0.7, 0.7, 0.7))
            return

        y_text += 20
        # Org info
        org_name = (signer.org_name or "").upper()
        page.insert_text(fitz.Point(x + 10, y_text), org_name[:50], fontsize=7, fontname="helv", color=VALUE_COLOR)
        if signer.org_bin:
            y_text += 10
            page.insert_text(fitz.Point(x + 10, y_text), f"БИН/ИИН: {signer.org_bin}", fontsize=7, fontname="helv", color=VALUE_COLOR)

        y_text += 18
        # Date parsing helper
        def get_date_only(dt_str: str):
            if not dt_str: return "—"
            return dt_str.split('T')[0] if 'T' in dt_str else dt_str.split(' ')[0]

        # Fields
        fields = [
            ("ФИО", signer.full_name),
            ("Права", signer.signer_title or "Первый руководитель"),
            ("Сертификат", signer.cert_serial[:30] + "..."),
            ("Период", f"с {get_date_only(signer.cert_valid_from)} до {get_date_only(signer.cert_valid_to)}"),
            ("Дата подписи", signer.signed_at),
        ]
        
        for label, val in fields:
            page.insert_text(fitz.Point(x + 10, y_text), label, fontsize=6.5, fontname="helv", color=LABEL_COLOR)
            page.insert_text(fitz.Point(x + 65, y_text), val[:50], fontsize=7, fontname="helv", color=VALUE_COLOR)
            y_text += 10
        
        # QR Code in the corner of the box
        if config.doc_url:
            try:
                qr_bytes = _generate_qr_png(config.doc_url + f"?role={signer.role}")
                qr_size = 55
                qr_rect = fitz.Rect(x + box_width - qr_size - 5, y + 175 - qr_size - 5, x + box_width - 5, y + 175 - 5)
                page.insert_image(qr_rect, stream=qr_bytes)
            except Exception as e:
                logger.warning("QR generation failed: %s", e)

    # Draw both boxes
    draw_signer_box(margin, footer_top, config.sender, True)
    draw_signer_box(margin + box_width + 20, footer_top, config.receiver, False)


def _generate_qr_png(data: str) -> bytes:
    """Generate a QR code as PNG bytes."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def stamp_document_pdf(
    pdf_path: str,
    output_path: str | None = None,
    config: StampConfig | None = None,
) -> str:
    """
    High-level function to stamp a PDF file on disk.
    Returns the path to the stamped PDF.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    if config is None:
        config = StampConfig()

    stamped_bytes = add_stamp_to_pdf(pdf_bytes, config)

    if output_path is None:
        # Overwrite the original
        output_path = pdf_path

    with open(output_path, "wb") as f:
        f.write(stamped_bytes)

    logger.info("PDF stamped successfully: %s (%d bytes)", output_path, len(stamped_bytes))
    return output_path
