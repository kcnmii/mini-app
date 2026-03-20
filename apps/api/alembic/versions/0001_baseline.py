"""baseline: all existing tables

Revision ID: 0001_baseline
Revises:
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── clients ──
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("bin_iin", sa.Text(), server_default=""),
        sa.Column("address", sa.Text(), server_default=""),
        sa.Column("director", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── client_bank_accounts ──
    op.create_table(
        "client_bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("iic", sa.Text(), server_default=""),
        sa.Column("bank_name", sa.Text(), server_default=""),
        sa.Column("bic", sa.Text(), server_default=""),
        sa.Column("kbe", sa.Text(), server_default=""),
        sa.Column("is_main", sa.Integer(), server_default="0"),
    )

    # ── client_contacts ──
    op.create_table(
        "client_contacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), server_default=""),
        sa.Column("phone", sa.Text(), server_default=""),
        sa.Column("email", sa.Text(), server_default=""),
    )

    # ── catalog_items ──
    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), server_default="шт."),
        sa.Column("price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("sku", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── documents ──
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("client_name", sa.Text(), nullable=False),
        sa.Column("total_sum", sa.Text(), nullable=False),
        sa.Column("total_amount", sa.Float(), server_default="0.0"),
        sa.Column("total_sum_in_words", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.Text(), nullable=False),
        sa.Column("docx_path", sa.Text(), server_default=""),
        sa.Column("payload_json", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── document_items ──
    op.create_table(
        "document_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("price", sa.Text(), nullable=False),
        sa.Column("total", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), server_default=""),
    )

    # ── invoices ──
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_name", sa.Text(), server_default=""),
        sa.Column("client_bin", sa.Text(), server_default=""),
        sa.Column("deal_reference", sa.Text(), server_default=""),
        sa.Column("status", sa.Text(), server_default="draft"),
        sa.Column("total_amount", sa.Float(), server_default="0.0"),
        sa.Column("pdf_path", sa.Text(), server_default=""),
        sa.Column("docx_path", sa.Text(), server_default=""),
        sa.Column("payload_json", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── new_invoice_items ──
    op.create_table(
        "new_invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Float(), server_default="1.0"),
        sa.Column("unit", sa.Text(), server_default="шт."),
        sa.Column("price", sa.Float(), server_default="0.0"),
        sa.Column("total", sa.Float(), server_default="0.0"),
        sa.Column("code", sa.Text(), server_default=""),
    )

    # ── payments ──
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("source", sa.Text(), server_default="manual"),
        sa.Column("bank_transaction_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── bank_accounts ──
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("bank_name", sa.Text(), server_default=""),
        sa.Column("account_number", sa.Text(), server_default=""),
        sa.Column("bic", sa.Text(), server_default=""),
        sa.Column("currency", sa.Text(), server_default="KZT"),
        sa.Column("is_default", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── bank_transactions ──
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("sender_name", sa.Text(), server_default=""),
        sa.Column("sender_bin", sa.Text(), server_default=""),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("matched_invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_income", sa.Integer(), server_default="1"),
        sa.Column("doc_num", sa.Text(), server_default=""),
        sa.Column("is_processed", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── supplier_profile ──
    op.create_table(
        "supplier_profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, unique=True, index=True),
        sa.Column("company_name", sa.Text(), server_default=""),
        sa.Column("company_iin", sa.Text(), server_default=""),
        sa.Column("company_iic", sa.Text(), server_default=""),
        sa.Column("company_bic", sa.Text(), server_default=""),
        sa.Column("company_kbe", sa.Text(), server_default=""),
        sa.Column("beneficiary_bank", sa.Text(), server_default=""),
        sa.Column("payment_code", sa.Text(), server_default=""),
        sa.Column("supplier_name", sa.Text(), server_default=""),
        sa.Column("supplier_iin", sa.Text(), server_default=""),
        sa.Column("supplier_address", sa.Text(), server_default=""),
        sa.Column("executor_name", sa.Text(), server_default=""),
        sa.Column("position", sa.Text(), server_default=""),
        sa.Column("phone", sa.Text(), server_default=""),
        sa.Column("email", sa.Text(), server_default=""),
        sa.Column("logo_path", sa.Text(), server_default=""),
        sa.Column("signature_path", sa.Text(), server_default=""),
        sa.Column("stamp_path", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("bank_transactions")
    op.drop_table("bank_accounts")
    op.drop_table("payments")
    op.drop_table("new_invoice_items")
    op.drop_table("document_items")
    op.drop_table("invoices")
    op.drop_table("documents")
    op.drop_table("catalog_items")
    op.drop_table("client_contacts")
    op.drop_table("client_bank_accounts")
    op.drop_table("clients")
    op.drop_table("supplier_profile")
