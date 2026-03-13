from fastapi import APIRouter, HTTPException

from app.core.db import get_db
from app.schemas.catalog import CatalogItemCreate, CatalogItemRead

router = APIRouter(prefix="/catalog/items", tags=["catalog"])


@router.get("", response_model=list[CatalogItemRead])
async def list_catalog_items() -> list[CatalogItemRead]:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, name, unit, price, sku, created_at FROM catalog_items ORDER BY id DESC"
        ).fetchall()
    return [CatalogItemRead.model_validate(dict(row)) for row in rows]


@router.post("", response_model=CatalogItemRead)
async def create_catalog_item(payload: CatalogItemCreate) -> CatalogItemRead:
    with get_db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO catalog_items (name, unit, price, sku)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name, payload.unit, payload.price, payload.sku),
        )
        row = connection.execute(
            "SELECT id, name, unit, price, sku, created_at FROM catalog_items WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return CatalogItemRead.model_validate(dict(row))


@router.put("/{item_id}", response_model=CatalogItemRead)
async def update_catalog_item(item_id: int, payload: CatalogItemCreate) -> CatalogItemRead:
    with get_db() as connection:
        connection.execute(
            """
            UPDATE catalog_items
            SET name = ?, unit = ?, price = ?, sku = ?
            WHERE id = ?
            """,
            (payload.name, payload.unit, payload.price, payload.sku, item_id),
        )
        row = connection.execute(
            "SELECT id, name, unit, price, sku, created_at FROM catalog_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    return CatalogItemRead.model_validate(dict(row))


@router.delete("/{item_id}")
async def delete_catalog_item(item_id: int):
    with get_db() as connection:
        cursor = connection.execute("DELETE FROM catalog_items WHERE id = ?", (item_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Товар/услуга не найдена")
    return {"status": "ok"}
