from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db, Client
from app.schemas.client import ClientCreate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(db: Session = Depends(get_db)) -> list[ClientRead]:
    clients = db.query(Client).order_by(Client.id.desc()).all()
    return clients


@router.post("", response_model=ClientRead)
async def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> ClientRead:
    new_client = Client(
        name=payload.name,
        bin_iin=payload.bin_iin,
        contact_name=payload.contact_name,
        phone=payload.phone
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client


@router.put("/{client_id}", response_model=ClientRead)
async def update_client(client_id: int, payload: ClientCreate, db: Session = Depends(get_db)) -> ClientRead:
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    client.name = payload.name
    client.bin_iin = payload.bin_iin
    client.contact_name = payload.contact_name
    client.phone = payload.phone
    
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
async def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    db.delete(client)
    db.commit()
    return {"status": "ok"}
