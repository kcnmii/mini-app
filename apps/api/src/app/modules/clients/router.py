from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.db import get_db, Client, ClientBankAccount, ClientContact
from app.schemas.client import ClientCreate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(db: Session = Depends(get_db)) -> list[ClientRead]:
    # We use joinedload to prevent N+1 queries for nested data
    clients = db.query(Client).options(
        joinedload(Client.accounts),
        joinedload(Client.contacts)
    ).order_by(Client.id.desc()).all()
    return clients


@router.post("", response_model=ClientRead)
async def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> ClientRead:
    new_client = Client(
        name=payload.name,
        bin_iin=payload.bin_iin,
        address=payload.address,
        director=payload.director
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # Add accounts
    for acc in payload.accounts:
        new_acc = ClientBankAccount(
            client_id=new_client.id,
            iic=acc.iic,
            bank_name=acc.bank_name,
            bic=acc.bic,
            kbe=acc.kbe,
            is_main=1 if acc.is_main else 0
        )
        db.add(new_acc)

    # Add contacts
    for con in payload.contacts:
        new_con = ClientContact(
            client_id=new_client.id,
            name=con.name,
            phone=con.phone,
            email=con.email
        )
        db.add(new_con)

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
    client.address = payload.address
    client.director = payload.director
    
    # Simple strategy: clear and recreate accounts/contacts
    # For more production-level, we would differentiate by ID
    db.query(ClientBankAccount).filter(ClientBankAccount.client_id == client_id).delete()
    db.query(ClientContact).filter(ClientContact.client_id == client_id).delete()

    for acc in payload.accounts:
        new_acc = ClientBankAccount(
            client_id=client_id,
            iic=acc.iic,
            bank_name=acc.bank_name,
            bic=acc.bic,
            kbe=acc.kbe,
            is_main=1 if acc.is_main else 0
        )
        db.add(new_acc)

    for con in payload.contacts:
        new_con = ClientContact(
            client_id=client_id,
            name=con.name,
            phone=con.phone,
            email=con.email
        )
        db.add(new_con)

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
