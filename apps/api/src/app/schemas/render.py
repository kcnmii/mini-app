from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class InvoiceItemPayload(BaseModel):
    number: int
    name: str
    quantity: str
    unit: str
    price: str
    total: str
    code: str = ""


class InvoiceRenderPayload(BaseModel):
    invoice_number: str = Field(alias="INVOICE_NUMBER")
    invoice_date: str = Field(alias="INVOICE_DATE")
    contract: str = Field(alias="CONTRACT")
    supplier_name: str = Field(alias="SUPPLIER_NAME")
    supplier_iin: str = Field(alias="SUPPLIER_IIN")
    supplier_address: str = Field(alias="SUPPLIER_ADDRESS")
    company_name: str = Field(alias="COMPANY_NAME")
    company_iin: str = Field(alias="COMPANY_IIN")
    company_iic: str = Field(alias="COMPANY_IIC")
    company_bic: str = Field(alias="COMPANY_BIC")
    company_kbe: str = Field(alias="COMPANY_KBE")
    beneficiary_bank: str = Field(alias="BENEFICIARY_BANK")
    payment_code: str = Field(alias="PAYMENT_CODE")
    client_name: str = Field(alias="CLIENT_NAME")
    client_iin: str = Field(alias="CLIENT_IIN")
    client_address: str = Field(alias="CLIENT_ADDRESS")
    executor_name: str = Field(alias="EXECUTOR_NAME")
    position: str = Field(alias="POSITION")
    vat: str = Field(alias="VAT")
    items_total_line: str = Field(alias="ITEMS_TOTAL_LINE")
    total_sum: str = Field(alias="TOTAL_SUM")
    total_sum_in_words: str = Field(alias="TOTAL_SUM_IN_WORDS")
    items: list[InvoiceItemPayload]

    # Image toggle flags — when False, image is excluded from the doc
    include_logo: bool = Field(default=True, alias="INCLUDE_LOGO")
    include_signature: bool = Field(default=True, alias="INCLUDE_SIGNATURE")
    include_stamp: bool = Field(default=True, alias="INCLUDE_STAMP")

    model_config = {"populate_by_name": True}

    def to_template_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "INVOICE_NUMBER": self.invoice_number,
            "INVOICE_DATE": self.invoice_date,
            "CONTRACT": self.contract,
            "SUPPLIER_NAME": self.supplier_name,
            "SUPPLIER_IIN": self.supplier_iin,
            "SUPPLIER_ADDRESS": self.supplier_address,
            "COMPANY_NAME": self.company_name,
            "COMPANY_IIN": self.company_iin,
            "COMPANY_IIC": self.company_iic,
            "COMPANY_BIC": self.company_bic,
            "COMPANY_KBE": self.company_kbe,
            "BENEFICIARY_BANK": self.beneficiary_bank,
            "PAYMENT_CODE": self.payment_code,
            "CLIENT_NAME": self.client_name,
            "CLIENT_IIN": self.client_iin,
            "CLIENT_ADDRESS": self.client_address,
            "EXECUTOR_NAME": self.executor_name,
            "POSITION": self.position,
            "VAT": self.vat,
            "ITEMS_TOTAL_LINE": self.items_total_line,
            "TOTAL_SUM": self.total_sum,
            "TOTAL_SUM_IN_WORDS": self.total_sum_in_words,
            "items": [item.model_dump() for item in self.items],
        }

        # Load images from profile uploads if toggles are on
        data["LOGO"] = _load_image_b64("logo") if self.include_logo else ""
        data["SIG"] = _load_image_b64("signature") if self.include_signature else ""
        data["STAMP"] = _load_image_b64("stamp") if self.include_stamp else ""

        return data


def _load_image_b64(image_type: str) -> str:
    """Read uploaded image file and return raw base64 (no data-uri prefix)."""
    from app.core.db import get_db

    path_column = f"{image_type}_path"
    try:
        with get_db() as conn:
            row = conn.execute(
                f"SELECT {path_column} FROM supplier_profile WHERE id = 1"
            ).fetchone()
            if not row:
                return ""
            file_path = dict(row).get(path_column, "")
            if not file_path:
                return ""
            p = Path(file_path)
            if not p.exists():
                return ""
            return base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return ""


class RenderInfoResponse(BaseModel):
    template_key: str
    template_version: str
    filename: str
