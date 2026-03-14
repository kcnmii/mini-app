from __future__ import annotations

from typing import Iterator
from sqlalchemy import create_engine, Column, Integer, Text, Float, DateTime, ForeignKey, String, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from app.core.config import settings

# Base class for SQLAlchemy models
Base = declarative_base()

# ── Models ──

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
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
    name = Column(Text, nullable=False)
    unit = Column(Text, default="шт.")
    price = Column(Float, nullable=False, default=0.0)
    sku = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    client_name = Column(Text, nullable=False)
    total_sum = Column(Text, nullable=False)
    total_sum_in_words = Column(Text, nullable=False)
    pdf_path = Column(Text, nullable=False)
    payload_json = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

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

class SupplierProfile(Base):
    __tablename__ = "supplier_profile"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(Text, default="")
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
    logo_path = Column(Text, default="")
    signature_path = Column(Text, default="")
    stamp_path = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

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
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        
    return create_engine(db_url, connect_args=connect_args)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
