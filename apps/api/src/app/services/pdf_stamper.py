"""
PDF Stamp Service — Adds ЭДО header and signature footer to PDF documents.

Uses PyMuPDF (fitz) to draw directly on existing PDFs.

Header (top of EVERY page):
  - "Документ зарегистрирован и подписан с помощью сервиса ЭДО"
  - MD5 Hash, Links for sender/receiver

Footer (SEPARATE last page):
  - Signature table with sender and receiver data
  - QR codes linking to the document page for each signer
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass, field
from typing import List

import fitz  # PyMuPDF
import qrcode

logger = logging.getLogger(__name__)


def _find_font(candidate_paths: list[str]) -> str | None:
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return None


FONT_REGULAR_PATH = _find_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
])
FONT_BOLD_PATH = _find_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
])


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
    iin: str = ""  # ИИН подписанта


@dataclass
class StampConfig:
    """Configuration for the PDF stamp."""
    doc_url: str = ""
    md5_hash: str = ""
    sender: SignerInfo | None = None
    receiver: SignerInfo | None = None
    edo_service_name: str = "ЭДО Doc App"
    edo_service_url: str = "https://doc.onlink.kz"


def _register_fonts(page: fitz.Page) -> tuple[str, str]:
    """Register Cyrillic-capable TrueType fonts and return (regular, bold) fontnames."""
    fn_r = "helv"
    fn_b = "helv"

    if FONT_REGULAR_PATH:
        page.insert_font(fontname="djvs", fontfile=FONT_REGULAR_PATH)
        fn_r = "djvs"

    if FONT_BOLD_PATH:
        page.insert_font(fontname="djvb", fontfile=FONT_BOLD_PATH)
        fn_b = "djvb"
    else:
        fn_b = fn_r  # fallback bold to regular

    return fn_r, fn_b


# ── Header height constant ──
HEADER_HEIGHT = 60


def add_stamp_to_pdf(
    pdf_bytes: bytes,
    config: StampConfig,
) -> bytes:
    """
    Add a header (top of EVERY page) and a signature footer (on a NEW last page)
    to an existing PDF. Returns the stamped PDF bytes.
    """
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    dst = fitz.open()  # new blank document

    try:
        for i in range(src.page_count):
            src_page = src[i]
            pw = src_page.rect.width
            ph = src_page.rect.height

            # Create a taller page: header + original content
            new_page = dst.new_page(width=pw, height=ph + HEADER_HEIGHT)

            # 1) Draw header at the top of the new page
            _draw_header_on_page(new_page, config, pw)

            # 2) Overlay the original page content shifted down by HEADER_HEIGHT
            new_page.show_pdf_page(
                fitz.Rect(0, HEADER_HEIGHT, pw, ph + HEADER_HEIGHT),
                src,
                i,
            )

        # ── Add footer on a SEPARATE new last page ──
        if config.sender or config.receiver:
            # Use same width as last source page
            last_w = src[-1].rect.width if src.page_count > 0 else 595
            last_h = src[-1].rect.height if src.page_count > 0 else 842
            _add_footer_page(dst, config, last_w, last_h)

        output = dst.tobytes(deflate=True, garbage=4)
    finally:
        src.close()
        dst.close()

    return output


def _draw_header_on_page(page: fitz.Page, config: StampConfig, width: float):
    """Draw ЭДО header at the top of the page — plain text, no background boxes.
    Must be called on a page that has HEADER_HEIGHT extra space at top."""

    font_r, font_b = _register_fonts(page)

    DARK = (0.1, 0.1, 0.1)
    GRAY = (0.35, 0.35, 0.4)
    BLUE = (0.0, 0.2, 0.6)
    margin = 30

    y = 12

    # Line 1: Main title
    page.insert_text(
        fitz.Point(margin, y),
        "Документ зарегистрирован и подписан с помощью сервиса электронного документооборота Onlink.kz (https://onlink.kz)",
        fontsize=7,
        fontname=font_r,
        color=DARK,
    )

    # Line 2: MD5 Hash
    y += 11
    if config.md5_hash:
        page.insert_text(
            fitz.Point(margin, y),
            f"MD5 Hash документа: {config.md5_hash}",
            fontsize=7,
            fontname=font_r,
            color=DARK,
        )

    # Line 3: Links
    y += 11
    if config.doc_url:
        page.insert_text(
            fitz.Point(margin, y),
            "Ссылка на электронный документ:",
            fontsize=7,
            fontname=font_r,
            color=DARK,
        )
        y += 10
        page.insert_text(
            fitz.Point(margin, y),
            f"Для отправителя - {config.doc_url}?category_id=1",
            fontsize=6.5,
            fontname=font_r,
            color=BLUE,
        )
        y += 10
        page.insert_text(
            fitz.Point(margin, y),
            f"Для получателя - {config.doc_url}?category_id=6",
            fontsize=6.5,
            fontname=font_r,
            color=BLUE,
        )

    # Thin separator line below header
    y += 6
    page.draw_line(
        fitz.Point(margin, HEADER_HEIGHT - 2),
        fitz.Point(width - margin, HEADER_HEIGHT - 2),
        color=(0.7, 0.7, 0.7),
        width=0.5,
    )


def _add_footer_page(doc: fitz.Document, config: StampConfig, page_width: float, page_height: float):
    """Add a new page at the end with the signature table — Uchet.EDO style."""

    # Insert a new page at the end
    new_page = doc.new_page(width=page_width, height=page_height)

    # Register fonts
    font_r, font_b = _register_fonts(new_page)

    DARK = (0.1, 0.1, 0.1)
    LABEL_COLOR = (0.3, 0.3, 0.35)
    BORDER_COLOR = (0.0, 0.0, 0.0)  # Black borders like reference

    margin = 30
    y_start = 40
    usable_width = page_width - 2 * margin

    # ── Title "подпись" ──
    new_page.insert_text(
        fitz.Point(margin, y_start),
        "подпись",
        fontsize=8,
        fontname=font_r,
        color=DARK,
    )

    y_start += 8

    # ── Draw the two-column signature table ──
    col_width = usable_width / 2
    row_height = 12
    qr_size = 65
    pad = 8  # inner padding from column edge

    signers = []
    if config.sender:
        signers.append(("Отправитель", config.sender, True))
    if config.receiver:
        signers.append(("Получатель", config.receiver, False))

    if not signers:
        return

    table_top = y_start
    max_y_bottom = table_top

    def _split_text(text: str, max_chars: int) -> list[str]:
        """Simple word wrap into lines of max_chars length."""
        words = text.split()
        lines = []
        cur = []
        cur_len = 0
        for w in words:
            # +1 for space if cur is not empty
            space = 1 if cur else 0
            if cur_len + len(w) + space > max_chars:
                if cur:
                    lines.append(" ".join(cur))
                    cur = [w]
                    cur_len = len(w)
                else:
                    # Single word is longer than max_chars, split it
                    lines.append(w[:max_chars])
                    cur = [w[max_chars:]]
                    cur_len = len(cur[0])
            else:
                cur.append(w)
                cur_len += len(w) + space
        if cur:
            lines.append(" ".join(cur))
        return lines

    def _draw_signer_column(x_start: float, signer: SignerInfo, role_label: str) -> float:
        """Draw one signer's info strictly within its column and return the final Y coordinate."""
        x = x_start + pad
        y = table_top + 14

        # ── Role label (bold, on its own line) ──
        org_display = signer.org_name or ""
        bin_display = f"({signer.org_bin})" if signer.org_bin else ""
        org_line = f"{org_display} {bin_display}".strip()

        new_page.insert_text(
            fitz.Point(x, y),
            role_label,
            fontsize=7.5,
            fontname=font_b,
            color=DARK,
        )

        # ── Org name + BIN on next line(s), wrapped within column ──
        if org_line:
            y += 11
            # Roughly 55 chars fit in the column at 7pt font
            org_lines = _split_text(org_line, max_chars=55)
            for line in org_lines:
                new_page.insert_text(
                    fitz.Point(x, y),
                    line,
                    fontsize=7,
                    fontname=font_r,
                    color=DARK,
                )
                y += 10
            y += 4

        y += 6

        # ── Data fields ──
        fields = [
            ("ФИО", f"{signer.full_name} {signer.iin}".strip() if signer.iin else signer.full_name),
            ("Права подписанта", signer.signer_title or "Первый руководитель"),
            ("Период действия сертификата",
             f"с {signer.cert_valid_from} по {signer.cert_valid_to}"
             if signer.cert_valid_from and signer.cert_valid_to else "—"),
            ("", ""),  # blank separator
            ("Серийный номер сертификата", signer.cert_serial or "—"),
            ("Дата подписания", signer.signed_at or "—"),
        ]

        for label, val in fields:
            if not label and not val:
                y += 4
                continue

            new_page.insert_text(
                fitz.Point(x, y),
                label,
                fontsize=6.5,
                fontname=font_b,
                color=LABEL_COLOR,
            )
            y += 10

            if val:
                val_str = str(val)
                # Value is indented by 12, so slightly fewer chars fit (~50)
                val_lines = _split_text(val_str, max_chars=50)
                for line in val_lines:
                    new_page.insert_text(
                        fitz.Point(x + 12, y),
                        line,
                        fontsize=7,
                        fontname=font_r,
                        color=DARK,
                    )
                    y += 10
            y += 4

        # ── QR Code — placed BELOW all text, never overlapping ──
        y += 6
        if config.doc_url:
            try:
                qr_url = f"{config.doc_url}?role={signer.role}"
                qr_bytes = _generate_qr_png(qr_url)
                qr_rect = fitz.Rect(x, y, x + qr_size, y + qr_size)
                new_page.insert_image(qr_rect, stream=qr_bytes)
                y += qr_size
            except Exception as e:
                logger.warning("QR generation failed for %s: %s", signer.role, e)
        
        return y + 10  # Return bottom-most Y coordinate with some padding

    # Draw each signer in their column and keep track of max Y
    for role_label, signer, is_sender in signers:
        if is_sender:
            col_y = _draw_signer_column(margin, signer, role_label)
        else:
            col_y = _draw_signer_column(margin + col_width, signer, role_label)
        max_y_bottom = max(max_y_bottom, col_y)

    # If only sender signed, show "Получатель" column with "ОЖИДАНИЕ ПОДПИСИ"
    if config.sender and not config.receiver:
        x = margin + col_width + pad
        y = table_top + 14
        new_page.insert_text(
            fitz.Point(x, y),
            "Получатель",
            fontsize=7.5,
            fontname=font_b,
            color=DARK,
        )
        y += 30
        new_page.insert_text(
            fitz.Point(x, y),
            "Ожидание подписи...",
            fontsize=8,
            fontname=font_r,
            color=(0.6, 0.6, 0.6),
        )
        max_y_bottom = max(max_y_bottom, y + 20)

    # If only receiver signed, show "Отправитель" column with "ОЖИДАНИЕ ПОДПИСИ"
    if config.receiver and not config.sender:
        x = margin + pad
        y = table_top + 14
        new_page.insert_text(
            fitz.Point(x, y),
            "Отправитель",
            fontsize=7.5,
            fontname=font_b,
            color=DARK,
        )
        y += 30
        new_page.insert_text(
            fitz.Point(x, y),
            "Ожидание подписи...",
            fontsize=8,
            fontname=font_r,
            color=(0.6, 0.6, 0.6),
        )
        max_y_bottom = max(max_y_bottom, y + 20)

    # ── AFTER drawing text, draw the table borders around it ──
    table_height = max_y_bottom - table_top
    table_rect = fitz.Rect(margin, table_top, margin + usable_width, table_top + table_height)
    new_page.draw_rect(table_rect, color=BORDER_COLOR, width=0.8)

    # Draw vertical divider between columns
    mid_x = margin + col_width
    new_page.draw_line(
        fitz.Point(mid_x, table_top),
        fitz.Point(mid_x, table_top + table_height),
        color=BORDER_COLOR,
        width=0.8,
    )


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
        output_path = pdf_path

    with open(output_path, "wb") as f:
        f.write(stamped_bytes)

    logger.info("PDF stamped successfully: %s (%d bytes)", output_path, len(stamped_bytes))
    return output_path
