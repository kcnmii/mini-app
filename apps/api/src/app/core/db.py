from __future__ import annotations

from typing import Iterator
from sqlalchemy import create_engine, Column, Integer, Text, Float, DateTime, ForeignKey, BigInteger, String, func, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from app.core.config import settings

# Base class for SQLAlchemy models
Base = declarative_base()

# ── Models ──

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    name = Column(Text, nullable=False)
    bin_iin = Column(Text, default="")
    address = Column(Text, default="")
    director = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    accounts = relationship("ClientBankAccount", backref="client", cascade="all, delete-orphan")
    contacts = relationship("ClientContact", backref="client", cascade="all, delete-orphan")

class ClientBankAccount(Base):
    __tablename__ = "client_bank_accounts"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    iic = Column(Text, default="")
    bank_name = Column(Text, default="")
    bic = Column(Text, default="")
    kbe = Column(Text, default="")
    is_main = Column(Integer, default=0) # 0 or 1

class ClientContact(Base):
    __tablename__ = "client_contacts"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, default="")
    phone = Column(Text, default="")
    email = Column(Text, default="")

class CatalogItem(Base):
    __tablename__ = "catalog_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    name = Column(Text, nullable=False)
    unit = Column(Text, default="шт.")
    price = Column(Float, nullable=False, default=0.0)
    sku = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    title = Column(Text, nullable=False)
    client_name = Column(Text, nullable=False)
    total_sum = Column(Text, nullable=False)
    total_amount = Column(Float, default=0.0)
    total_sum_in_words = Column(Text, nullable=False)
    pdf_path = Column(Text, nullable=False)
    docx_path = Column(Text, default="")
    payload_json = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    # ── EDO fields ──
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True)
    doc_type = Column(String(20), default="invoice")  # invoice | act | waybill | esf
    edo_status = Column(String(30), default="draft")   # draft | awaiting_sign | signed_self | sent | signed_both | rejected | esf_pending | esf_submitted | completed
    share_uuid = Column(String(36), nullable=True, unique=True, index=True)
    sender_user_id = Column(BigInteger, nullable=True)
    receiver_bin = Column(String(12), default="")
    receiver_name = Column(Text, default="")
    md5_hash = Column(String(32), default="")
    signed_at = Column(DateTime, nullable=True)
    countersigned_at = Column(DateTime, nullable=True)

class DocumentItem(Base):
    __tablename__ = "document_items"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    quantity = Column(Text, nullable=False)
    unit = Column(Text, nullable=False)
    price = Column(Text, nullable=False)
    total = Column(Text, nullable=False)
    code = Column(Text, default="")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    number = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False, server_default=func.now())
    due_date = Column(DateTime, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    client_name = Column(Text, default="")
    client_bin = Column(Text, default="")
    deal_reference = Column(Text, default="")
    payment_code = Column(Text, default="")
    status = Column(Text, default="draft")  # draft | sent | paid | overdue
    total_amount = Column(Float, default=0.0)
    pdf_path = Column(Text, default="")
    docx_path = Column(Text, default="")
    payload_json = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="invoices")
    line_items = relationship("NewInvoiceItem", backref="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", backref="invoice", cascade="all, delete-orphan")


class NewInvoiceItem(Base):
    __tablename__ = "new_invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    catalog_item_id = Column(Integer, ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)
    name = Column(Text, nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(Text, default="шт.")
    price = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    code = Column(Text, default="")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, server_default=func.now())
    source = Column(Text, default="manual")  # manual | bank_import
    bank_transaction_id = Column(Integer, nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    bank_name = Column(Text, default="")
    account_number = Column(Text, default="") # IIC
    bic = Column(Text, default="")
    currency = Column(Text, default="KZT")
    is_default = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class SupplierProfile(Base):
    __tablename__ = "supplier_profile"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, unique=True, index=True)
    company_name = Column(Text, default="")
    notifications_enabled = Column(Boolean, default=True)
    company_iin = Column(Text, default="")
    company_iic = Column(Text, default="")
    company_bic = Column(Text, default="")
    company_kbe = Column(Text, default="")
    beneficiary_bank = Column(Text, default="")
    payment_code = Column(Text, default="")
    supplier_name = Column(Text, default="")
    supplier_iin = Column(Text, default="")
    supplier_address = Column(Text, default="")
    executor_name = Column(Text, default="")
    position = Column(Text, default="")
    phone = Column(Text, default="")
    email = Column(Text, default="")
    notifications_enabled = Column(Boolean, default=True)
    logo_path = Column(Text, default="")
    signature_path = Column(Text, default="")
    stamp_path = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ── EDO Models ──

class Contract(Base):
    """Договор с контрагентом."""
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    number = Column(String(50), nullable=False)
    date = Column(DateTime, nullable=True)
    counterparty_name = Column(Text, default="")
    counterparty_bin = Column(String(12), default="")
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="active")  # active, completed, terminated
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Signature(Base):
    """ЭЦП-подпись документа (CMS / XML Dsig)."""
    __tablename__ = "signatures"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    signer_iin = Column(String(12), nullable=False)
    signer_name = Column(Text, default="")
    signer_org_name = Column(Text, default="")
    signer_role = Column(String(20), default="sender")  # sender | receiver
    certificate_serial = Column(Text, default="")
    certificate_valid_from = Column(DateTime, nullable=True)
    certificate_valid_to = Column(DateTime, nullable=True)
    signature_data = Column(Text, nullable=False)  # Base64 CMS or XML Dsig
    signature_type = Column(String(10), default="cms")  # cms | xml
    signed_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", backref="signatures")


class SigningSession(Base):
    """Активная сессия подписания через SIGEX/eGov Mobile."""
    __tablename__ = "signing_sessions"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)
    sign_url = Column(Text, nullable=False)
    egov_mobile_link = Column(Text, default="")
    egov_business_link = Column(Text, default="")
    qr_code_b64 = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending | signed | expired | error
    signer_role = Column(String(20), default="sender")  # sender | receiver
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", backref="signing_sessions")


class EsfRecord(Base):
    """Запись об ЭСФ отправленной в КГД."""
    __tablename__ = "esf_records"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    esf_number = Column(String(50), default="")
    esf_xml = Column(Text, default="")
    signed_esf_xml = Column(Text, default="")
    session_id = Column(String(100), default="")
    kgd_status = Column(String(30), default="pending")  # pending, submitted, accepted, rejected
    kgd_response = Column(Text, default="")
    submitted_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)  # 15 calendar days
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", backref="esf_records")


class DocumentShare(Base):
    """Шаринг документа контрагенту (ссылка / email / Telegram)."""
    __tablename__ = "document_shares"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    share_uuid = Column(String(36), nullable=False, unique=True, index=True)
    share_type = Column(String(20), default="link")  # link | email | telegram
    recipient_email = Column(Text, default="")
    recipient_name = Column(Text, default="")
    recipient_bin = Column(String(12), default="")
    accessed_at = Column(DateTime, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", backref="shares")

# ── Database Initialization ──

def get_engine():
    db_url = settings.database_url
    if not db_url:
        # Fallback to SQLite
        db_url = f"sqlite:///{settings.sqlite_path}"
    
    # Handle PostgreSQL async vs sync if needed, but here we use sync psycopg
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        
    connect_args = {}
    pool_kwargs = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        # PostgreSQL: enable connection pooling for faster responses
        pool_kwargs = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
        
    return create_engine(db_url, connect_args=connect_args, **pool_kwargs)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """Initialize database.
    
    Schema management is handled by Alembic migrations (run via entrypoint.sh).
    This function only ensures the data directory exists for SQLite fallback.
    """
    db_url = settings.database_url or f"sqlite:///{settings.sqlite_path}"
    if db_url.startswith("sqlite"):
        import os
        db_file = settings.sqlite_path
        db_dir = os.path.dirname(db_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        # For SQLite (local dev without Alembic), create tables directly
        Base.metadata.create_all(bind=engine)

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
