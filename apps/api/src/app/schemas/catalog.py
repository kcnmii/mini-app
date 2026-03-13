from pydantic import BaseModel


class CatalogItemCreate(BaseModel):
    name: str
    unit: str = "шт."
    price: float = 0
    sku: str = ""


class CatalogItemRead(CatalogItemCreate):
    id: int
    created_at: str
