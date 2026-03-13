from fastapi import APIRouter, HTTPException

from app.core.db import get_db
from app.schemas.client import ClientCreate, ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients() -> list[ClientRead]:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, name, bin_iin, contact_name, phone, created_at FROM clients ORDER BY id DESC"
        ).fetchall()
    return [ClientRead.model_validate(dict(row)) for row in rows]


@router.post("", response_model=ClientRead)
async def create_client(payload: ClientCreate) -> ClientRead:
    with get_db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO clients (name, bin_iin, contact_name, phone)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name, payload.bin_iin, payload.contact_name, payload.phone),
        )
        row = connection.execute(
            "SELECT id, name, bin_iin, contact_name, phone, created_at FROM clients WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return ClientRead.model_validate(dict(row))
@router.put("/{client_id}", response_model=ClientRead)
async def update_client(client_id: int, payload: ClientCreate) -> ClientRead:
    with get_db() as connection:
        connection.execute(
            """
            UPDATE clients 
            SET name = ?, bin_iin = ?, contact_name = ?, phone = ?
            WHERE id = ?
            """,
            (payload.name, payload.bin_iin, payload.contact_name, payload.phone, client_id),
        )
        row = connection.execute(
            "SELECT id, name, bin_iin, contact_name, phone, created_at FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()
    return ClientRead.model_validate(dict(row))


@router.delete("/{client_id}")
async def delete_client(client_id: int):
    with get_db() as connection:
        cursor = connection.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Клиент не найден")
    return {"status": "ok"}
