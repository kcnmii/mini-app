"""Phase 1 tests — Invoice CRUD, statuses, payments, dashboard, auth.

Run:  cd apps/api && python -m pytest tests/test_phase1_invoices.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Generator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ── Path setup ──
API_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if API_SRC not in sys.path:
    sys.path.insert(0, API_SRC)

os.environ.setdefault("SQLITE_PATH", ":memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "fake")

from app.core.db import Base, Invoice, NewInvoiceItem, Payment, Client  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.core.db import get_db  # noqa: E402

# ── Fixtures ──

TEST_USER_ID = 123456789
JWT_SECRET = "test-secret"


def _make_token(user_id: int = TEST_USER_ID) -> str:
    return jwt.encode({"sub": str(user_id)}, JWT_SECRET, algorithm="HS256")


AUTH_HEADER = {"Authorization": f"Bearer {_make_token()}"}


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionTesting = sessionmaker(bind=engine)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_client(db_session: Session) -> Client:
    cl = Client(user_id=TEST_USER_ID, name="ТОО Альфа", bin_iin="123456789012", address="Алматы")
    db_session.add(cl)
    db_session.commit()
    db_session.refresh(cl)
    return cl


# ── 1. Create Invoice ──

def test_create_invoice(client: TestClient, sample_client):
    resp = client.post(
        "/invoices",
        json={
            "number": "СФ-001",
            "client_id": sample_client.id,
            "client_name": "ТОО Альфа",
            "client_bin": "123456789012",
            "items": [
                {"name": "Разработка сайта", "quantity": 1, "unit": "шт.", "price": 500000, "total": 500000},
                {"name": "Хостинг", "quantity": 12, "unit": "мес.", "price": 5000, "total": 60000},
            ],
        },
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["number"] == "СФ-001"
    assert data["status"] == "draft"
    assert data["total_amount"] == 560000.0
    assert len(data["line_items"]) == 2
    assert data["client_name"] == "ТОО Альфа"


# ── 2. List Invoices with filter ──

def test_list_invoices(client: TestClient, sample_client):
    # Create two invoices
    client.post("/invoices", json={"number": "СФ-001", "client_name": "A", "items": [{"name": "X", "quantity": 1, "price": 100, "total": 100}]}, headers=AUTH_HEADER)
    client.post("/invoices", json={"number": "СФ-002", "client_name": "B", "items": [{"name": "Y", "quantity": 1, "price": 200, "total": 200}]}, headers=AUTH_HEADER)

    # List all
    resp = client.get("/invoices", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Filter by status=draft
    resp = client.get("/invoices?status=draft", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Filter by status=paid (none)
    resp = client.get("/invoices?status=paid", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ── 3. Get Invoice detail ──

def test_get_invoice_detail(client: TestClient):
    create_resp = client.post("/invoices", json={
        "number": "СФ-010",
        "client_name": "ТОО Бета",
        "deal_reference": "Договор №5",
        "items": [{"name": "Консалтинг", "quantity": 10, "unit": "час", "price": 15000, "total": 150000}],
    }, headers=AUTH_HEADER)
    inv_id = create_resp.json()["id"]

    resp = client.get(f"/invoices/{inv_id}", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["number"] == "СФ-010"
    assert data["deal_reference"] == "Договор №5"
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["name"] == "Консалтинг"


# ── 4. Update status to sent ──

def test_update_status_sent(client: TestClient):
    create_resp = client.post("/invoices", json={"number": "СФ-020", "client_name": "C", "items": [{"name": "Z", "quantity": 1, "price": 100, "total": 100}]}, headers=AUTH_HEADER)
    inv_id = create_resp.json()["id"]

    resp = client.patch(f"/invoices/{inv_id}/status", json={"status": "sent"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"

    # Verify invalid status
    resp = client.patch(f"/invoices/{inv_id}/status", json={"status": "garbage"}, headers=AUTH_HEADER)
    assert resp.status_code == 422


# ── 5. Mark as paid (creates Payment) ──

def test_mark_as_paid(client: TestClient):
    create_resp = client.post("/invoices", json={"number": "СФ-030", "client_name": "D", "items": [{"name": "W", "quantity": 1, "price": 75000, "total": 75000}]}, headers=AUTH_HEADER)
    inv_id = create_resp.json()["id"]

    # Mark as paid
    resp = client.post(f"/invoices/{inv_id}/pay", json={"note": "Kaspi перевод"}, headers=AUTH_HEADER)
    assert resp.status_code == 201
    payment = resp.json()
    assert payment["amount"] == 75000.0
    assert payment["source"] == "manual"
    assert payment["note"] == "Kaspi перевод"

    # Check invoice is now paid
    inv_resp = client.get(f"/invoices/{inv_id}", headers=AUTH_HEADER)
    assert inv_resp.json()["status"] == "paid"


# ── 6. Auto-overdue ──

def test_overdue_auto_update(client: TestClient, db_session: Session):
    # Create invoice with due_date in the past and status=sent
    past_due = datetime.now(timezone.utc) - timedelta(days=5)
    inv = Invoice(
        user_id=TEST_USER_ID,
        number="СФ-040",
        date=datetime.now(timezone.utc),
        due_date=past_due,
        client_name="E",
        status="sent",
        total_amount=100000,
    )
    db_session.add(inv)
    db_session.commit()

    # GET /invoices should trigger auto-overdue
    resp = client.get("/invoices", headers=AUTH_HEADER)
    assert resp.status_code == 200
    invoices = resp.json()
    overdue_inv = [i for i in invoices if i["number"] == "СФ-040"]
    assert len(overdue_inv) == 1
    assert overdue_inv[0]["status"] == "overdue"


# ── 7. Dashboard summary ──

def test_dashboard_summary(client: TestClient, db_session: Session):
    now = datetime.now(timezone.utc)

    # Create sent invoice (awaiting)
    inv1 = Invoice(user_id=TEST_USER_ID, number="D-001", date=now, client_name="F", status="sent", total_amount=200000)
    # Create overdue invoice
    inv2 = Invoice(user_id=TEST_USER_ID, number="D-002", date=now, due_date=now - timedelta(days=3), client_name="G", status="sent", total_amount=100000)
    # Create paid invoice
    inv3 = Invoice(user_id=TEST_USER_ID, number="D-003", date=now, client_name="H", status="paid", total_amount=300000)
    db_session.add_all([inv1, inv2, inv3])
    db_session.commit()

    # Add payment for the paid invoice
    p = Payment(user_id=TEST_USER_ID, invoice_id=inv3.id, amount=300000, source="manual")
    db_session.add(p)
    db_session.commit()

    resp = client.get("/dashboard/summary", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    # inv2 should be auto-marked overdue, so:
    # awaiting = inv1 (200000) + inv2-now-overdue (100000) = 300000
    assert data["awaiting"] == 300000.0
    # overdue = inv2 (100000)
    assert data["overdue"] == 100000.0
    assert data["overdue_count"] == 1
    # paid_this_month = 300000
    assert data["paid_this_month"] == 300000.0
    assert data["invoices_count"] == 3


# ── 8. Delete invoice ──

def test_delete_invoice(client: TestClient):
    create_resp = client.post("/invoices", json={"number": "СФ-DEL", "client_name": "X", "items": [{"name": "T", "quantity": 1, "price": 100, "total": 100}]}, headers=AUTH_HEADER)
    inv_id = create_resp.json()["id"]

    resp = client.delete(f"/invoices/{inv_id}", headers=AUTH_HEADER)
    assert resp.status_code == 200

    # Verify gone
    resp = client.get(f"/invoices/{inv_id}", headers=AUTH_HEADER)
    assert resp.status_code == 404


# ── 9. Next invoice number ──

def test_next_invoice_number(client: TestClient):
    # No invoices yet
    resp = client.get("/invoices/next-number", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["next_number"] == "СФ-001"

    # Create one
    client.post("/invoices", json={"number": "СФ-005", "client_name": "Y", "items": [{"name": "N", "quantity": 1, "price": 50, "total": 50}]}, headers=AUTH_HEADER)

    resp = client.get("/invoices/next-number", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["next_number"] == "СФ-006"


# ── 10. Unauthorized access ──

def test_unauthorized_access(client: TestClient):
    endpoints = [
        ("GET", "/invoices"),
        ("POST", "/invoices"),
        ("GET", "/invoices/1"),
        ("PATCH", "/invoices/1/status"),
        ("POST", "/invoices/1/pay"),
        ("DELETE", "/invoices/1"),
        ("GET", "/dashboard/summary"),
        ("GET", "/invoices/next-number"),
    ]
    for method, url in endpoints:
        resp = client.request(method, url)
        assert resp.status_code == 401, f"{method} {url} should require auth, got {resp.status_code}"
