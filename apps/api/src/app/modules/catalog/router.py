from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db, CatalogItem
from app.schemas.catalog import CatalogItemCreate, CatalogItemRead

router = APIRouter(prefix="/catalog/items", tags=["catalog"])


@router.get("", response_model=list[CatalogItemRead])
async def list_catalog_items(db: Session = Depends(get_db)) -> list[CatalogItemRead]:
    items = db.query(CatalogItem).order_by(CatalogItem.id.desc()).all()
    return items


@router.post("", response_model=CatalogItemRead)
async def create_catalog_item(payload: CatalogItemCreate, db: Session = Depends(get_db)) -> CatalogItemRead:
    new_item = CatalogItem(
        name=payload.name,
        unit=payload.unit,
        price=payload.price,
        sku=payload.sku
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.put("/{item_id}", response_model=CatalogItemRead)
async def update_catalog_item(item_id: int, payload: CatalogItemCreate, db: Session = Depends(get_db)) -> CatalogItemRead:
    item = db.query(CatalogItem).filter(CatalogItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Товар/услуга не найдена")
    
    item.name = payload.name
    item.unit = payload.unit
    item.price = payload.price
    item.sku = payload.sku
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
async def delete_catalog_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(CatalogItem).filter(CatalogItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Товар/услуга не найдена")
    db.delete(item)
    db.commit()
    return {"status": "ok"}
