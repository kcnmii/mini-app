from pydantic import BaseModel


class SupplierProfile(BaseModel):
    id: int = 0
    company_name: str = ""
    company_iin: str = ""
    company_iic: str = ""
    company_bic: str = ""
    company_kbe: str = ""
    beneficiary_bank: str = ""
    payment_code: str = ""
    supplier_name: str = ""
    supplier_iin: str = ""
    supplier_address: str = ""
    executor_name: str = ""
    position: str = ""
    phone: str = ""
    email: str = ""
    notifications_enabled: bool = True
    logo_path: str = ""
    signature_path: str = ""
    stamp_path: str = ""
    profile_uuid: str = ""


class SupplierProfileUpdate(BaseModel):
    company_name: str = ""
    company_iin: str = ""
    company_iic: str = ""
    company_bic: str = ""
    company_kbe: str = ""
    beneficiary_bank: str = ""
    payment_code: str = ""
    supplier_name: str = ""
    supplier_iin: str = ""
    supplier_address: str = ""
    executor_name: str = ""
    position: str = ""
    phone: str = ""
    email: str = ""
    notifications_enabled: bool = True
