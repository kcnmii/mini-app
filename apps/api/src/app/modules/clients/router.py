from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.db import get_db, Client, ClientBankAccount, ClientContact
from app.core.auth import get_current_user_id
from app.schemas.client import ClientCreate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/search-bin/{bin_number}")
async def search_bin(bin_number: str):
    """
    Search BIN/IIN details via eGov service (kyc.kz wrapper).
    """
    from app.services.egov import search_bin_details
    
    result = await search_bin_details(bin_number)
    if not result:
        raise HTTPException(status_code=404, detail="Организация не найдена")
    
    return result


@router.get("", response_model=list[ClientRead])
async def list_clients(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ClientRead]:
    clients = db.query(Client).options(
        joinedload(Client.accounts),
        joinedload(Client.contacts)
    ).filter(Client.user_id == user_id).order_by(Client.id.desc()).all()
    return clients


@router.post("", response_model=ClientRead)
async def create_client(
    payload: ClientCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ClientRead:
    new_client = Client(
        user_id=user_id,
        name=payload.name,
        bin_iin=payload.bin_iin,
        address=payload.address,
        director=payload.director,
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    for acc in payload.accounts:
        new_acc = ClientBankAccount(
            client_id=new_client.id,
            iic=acc.iic,
            bank_name=acc.bank_name,
            bic=acc.bic,
            kbe=acc.kbe,
            is_main=1 if acc.is_main else 0,
        )
        db.add(new_acc)

    for con in payload.contacts:
        new_con = ClientContact(
            client_id=new_client.id,
            name=con.name,
            phone=con.phone,
            email=con.email,
        )
        db.add(new_con)

    db.commit()
    db.refresh(new_client)
    return new_client


@router.put("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int,
    payload: ClientCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ClientRead:
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    client.name = payload.name
    client.bin_iin = payload.bin_iin
    client.address = payload.address
    client.director = payload.director

    db.query(ClientBankAccount).filter(ClientBankAccount.client_id == client_id).delete()
    db.query(ClientContact).filter(ClientContact.client_id == client_id).delete()

    for acc in payload.accounts:
        new_acc = ClientBankAccount(
            client_id=client_id,
            iic=acc.iic,
            bank_name=acc.bank_name,
            bic=acc.bic,
            kbe=acc.kbe,
            is_main=1 if acc.is_main else 0,
        )
        db.add(new_acc)

    for con in payload.contacts:
        new_con = ClientContact(
            client_id=client_id,
            name=con.name,
            phone=con.phone,
            email=con.email,
        )
        db.add(new_con)

    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    db.delete(client)
    db.commit()
    return {"status": "ok"}


@router.get("/{client_id}/balance")
async def get_client_balance(
    client_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from app.core.db import Invoice
    from sqlalchemy import func

    # Make sure client belongs to user
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Invoiced: all non-draft invoices
    total_invoiced = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0))
        .filter(Invoice.client_id == client_id, Invoice.status.in_(["sent", "paid", "overdue"]))
        .scalar()
    )

    # Paid: all paid invoices (we define 'paid' amount as the full amount for phase 5 simplicity)
    # or you could map to Payments if you want strictly real payments
    total_paid = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0.0))
        .filter(Invoice.client_id == client_id, Invoice.status == "paid")
        .scalar()
    )

    debt = float(total_invoiced) - float(total_paid)

    return {
        "total_invoiced": float(total_invoiced),
        "total_paid": float(total_paid),
        "debt": debt if debt > 0 else 0.0
    }
