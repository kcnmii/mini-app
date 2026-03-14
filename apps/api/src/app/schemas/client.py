import datetime
from typing import List, Optional
from pydantic import BaseModel


class ClientBankAccountSchema(BaseModel):
    id: Optional[int] = None
    iic: str = ""
    bank_name: str = ""
    bic: str = ""
    kbe: str = ""
    is_main: bool = False

class ClientContactSchema(BaseModel):
    id: Optional[int] = None
    name: str = ""
    phone: str = ""
    email: str = ""

class ClientCreate(BaseModel):
    name: str
    bin_iin: str = ""
    address: str = ""
    director: str = ""
    accounts: List[ClientBankAccountSchema] = []
    contacts: List[ClientContactSchema] = []


class ClientRead(BaseModel):
    id: int
    name: str
    bin_iin: str = ""
    address: str = ""
    director: str = ""
    created_at: Optional[datetime.datetime] = None
    accounts: List[ClientBankAccountSchema] = []
    contacts: List[ClientContactSchema] = []

    model_config = {"from_attributes": True}
