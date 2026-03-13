from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    bin_iin: str = ""
    contact_name: str = ""
    phone: str = ""


class ClientRead(ClientCreate):
    id: int
    created_at: str
