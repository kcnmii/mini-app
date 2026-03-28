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
    """Draw the ЭДО header at the top of the first page."""
    width = page.rect.width
    header_height = 60
    margin = 28
    font_size_small = 7
    font_size_tiny = 6

    # Shift existing content down by inserting space at the top
    # We do this by modifying the cropbox/mediabox
    original_rect = page.rect
    new_height = original_rect.height + header_height
    page.set_mediabox(fitz.Rect(0, -header_height, original_rect.width, original_rect.height))

    # Draw a light background for the header
    header_rect = fitz.Rect(0, -header_height, width, 0)
    page.draw_rect(header_rect, color=None, fill=(0.96, 0.97, 0.99))

    # Draw a bottom line
    page.draw_line(
        fitz.Point(margin, -1),
        fitz.Point(width - margin, -1),
        color=(0.8, 0.82, 0.85),
        width=0.5,
    )

    y = -header_height + 8

    # Line 1: Service info
    text_service = f"Документ зарегистрирован и подписан с помощью сервиса электронного документооборота ({config.edo_service_url})"
    page.insert_text(
        fitz.Point(margin, y + font_size_small),
        text_service,
        fontsize=font_size_small,
        fontname="helv",
        color=(0.3, 0.3, 0.3),
    )

    y += 12
    # Line 2: MD5
    if config.md5_hash:
        text_md5 = f"MD5 Hash документа: {config.md5_hash}"
        page.insert_text(
            fitz.Point(margin, y + font_size_tiny),
            text_md5,
            fontsize=font_size_tiny,
            fontname="helv",
            color=(0.4, 0.4, 0.4),
        )

    y += 10
    # Line 3: Link
    if config.doc_url:
        text_link = f"Ссылка на электронный документ: {config.doc_url}"
        page.insert_text(
            fitz.Point(margin, y + font_size_tiny),
            text_link,
            fontsize=font_size_tiny,
            fontname="helv",
            color=(0.0, 0.35, 0.7),
        )

    y += 10
    # Line 4: Sender/Receiver links
    if config.doc_url:
        sender_link = f"Для отправителя — {config.doc_url}?role=sender"
        receiver_link = f"Для получателя — {config.doc_url}?role=receiver"
        page.insert_text(
            fitz.Point(margin, y + font_size_tiny),
            sender_link,
            fontsize=font_size_tiny,
            fontname="helv",
            color=(0.0, 0.35, 0.7),
        )
        y += 9
        page.insert_text(
            fitz.Point(margin, y + font_size_tiny),
            receiver_link,
            fontsize=font_size_tiny,
            fontname="helv",
            color=(0.0, 0.35, 0.7),
        )


def _add_footer(page: fitz.Page, config: StampConfig):
    """Draw signature table at the bottom of the last page."""
    width = page.rect.width
    margin = 28
    footer_height = 180
    font_size = 7
    font_size_label = 6
    line_height = 10
    qr_size = 65

    # Extend page downward for footer
    original_rect = page.rect
    page.set_mediabox(fitz.Rect(
        original_rect.x0,
        original_rect.y0,
        original_rect.x1,
        original_rect.y1 + footer_height,
    ))

    footer_top = original_rect.height
    content_width = width - 2 * margin
    half = content_width / 2

    # Draw separator line
    page.draw_line(
        fitz.Point(margin, footer_top + 8),
        fitz.Point(width - margin, footer_top + 8),
        color=(0.7, 0.7, 0.7),
        width=0.5,
    )

    # Label "подпись"
    page.insert_text(
        fitz.Point(margin, footer_top + 20),
        "подпись",
        fontsize=8,
        fontname="helv",
        color=(0.4, 0.4, 0.4),
    )

    # Draw columns: Sender (left) | Receiver (right)
    col_x = [margin, margin + half + 10]
    signers = []
    if config.sender:
        signers.append((0, config.sender))
    if config.receiver:
        signers.append((1, config.receiver))

    for col_idx, signer in signers:
        x = col_x[col_idx]
        y_start = footer_top + 35

        # Vertical separator between columns
        if col_idx == 1:
            page.draw_line(
                fitz.Point(margin + half + 5, footer_top + 8),
                fitz.Point(margin + half + 5, footer_top + footer_height - 10),
                color=(0.8, 0.8, 0.8),
                width=0.5,
            )

        rows = [
            ("", f"{signer.role_label}"),
            ("", f"{signer.org_name}" + (f" ({signer.org_bin})" if signer.org_bin else "")),
            ("ФИО", signer.full_name),
            ("Права подписанта", signer.signer_title or "—"),
            ("Период действия сертификата", f"c {signer.cert_valid_from} по {signer.cert_valid_to}" if signer.cert_valid_from else "—"),
            ("Серийный номер сертификата", signer.cert_serial or "—"),
            ("Дата подписания", signer.signed_at or "—"),
        ]

        y = y_start
        for label, value in rows:
            if label:
                # Two-column within: label + value
                page.insert_text(
                    fitz.Point(x, y + font_size_label),
                    label,
                    fontsize=font_size_label,
                    fontname="helv",
                    color=(0.5, 0.5, 0.5),
                )
                page.insert_text(
                    fitz.Point(x + 95, y + font_size),
                    value[:45],
                    fontsize=font_size,
                    fontname="helv",
                    color=(0.15, 0.15, 0.15),
                )
            else:
                # Full-width label (role/org)
                page.insert_text(
                    fitz.Point(x, y + font_size),
                    value[:50],
                    fontsize=font_size,
                    fontname="helv",
                    color=(0.15, 0.15, 0.15),
                )
            y += line_height

        # QR code
        if config.doc_url:
            try:
                qr_bytes = _generate_qr_png(config.doc_url + f"?role={signer.role}")
                qr_rect = fitz.Rect(x, y + 4, x + qr_size, y + 4 + qr_size)
                page.insert_image(qr_rect, stream=qr_bytes)
            except Exception as exc:
                logger.warning("Failed to generate QR: %s", exc)


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
