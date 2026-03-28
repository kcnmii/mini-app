"""EDO tables: contracts, signatures, signing_sessions, esf_records, document_shares + Document EDO columns

Revision ID: 0005_edo_tables
Revises: e1f0b00bb6d8
Create Date: 2026-03-28 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_edo_tables'
down_revision: Union[str, None] = 'e1f0b00bb6d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    # ── 1. contracts table ──
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("counterparty_name", sa.Text(), server_default=""),
        sa.Column("counterparty_bin", sa.String(12), server_default=""),
        sa.Column("total_amount", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 2. signatures table ──
    op.create_table(
        "signatures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("signer_iin", sa.String(12), nullable=False),
        sa.Column("signer_name", sa.Text(), server_default=""),
        sa.Column("signer_org_name", sa.Text(), server_default=""),
        sa.Column("signer_role", sa.String(20), server_default="sender"),
        sa.Column("certificate_serial", sa.Text(), server_default=""),
        sa.Column("certificate_valid_from", sa.DateTime(), nullable=True),
        sa.Column("certificate_valid_to", sa.DateTime(), nullable=True),
        sa.Column("signature_data", sa.Text(), nullable=False),
        sa.Column("signature_type", sa.String(10), server_default="cms"),
        sa.Column("signed_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 3. signing_sessions table ──
    op.create_table(
        "signing_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("sign_url", sa.Text(), nullable=False),
        sa.Column("egov_mobile_link", sa.Text(), server_default=""),
        sa.Column("egov_business_link", sa.Text(), server_default=""),
        sa.Column("qr_code_b64", sa.Text(), server_default=""),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("signer_role", sa.String(20), server_default="sender"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 4. esf_records table ──
    op.create_table(
        "esf_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("esf_number", sa.String(50), server_default=""),
        sa.Column("esf_xml", sa.Text(), server_default=""),
        sa.Column("signed_esf_xml", sa.Text(), server_default=""),
        sa.Column("session_id", sa.String(100), server_default=""),
        sa.Column("kgd_status", sa.String(30), server_default="pending"),
        sa.Column("kgd_response", sa.Text(), server_default=""),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 5. document_shares table ──
    op.create_table(
        "document_shares",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("share_uuid", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("share_type", sa.String(20), server_default="link"),
        sa.Column("recipient_email", sa.Text(), server_default=""),
        sa.Column("recipient_name", sa.Text(), server_default=""),
        sa.Column("recipient_bin", sa.String(12), server_default=""),
        sa.Column("accessed_at", sa.DateTime(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 6. EDO columns on documents table ──
    if is_pg:
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS doc_type VARCHAR(20) DEFAULT 'invoice'")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS edo_status VARCHAR(30) DEFAULT 'draft'")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS share_uuid VARCHAR(36)")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS sender_user_id BIGINT")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS receiver_bin VARCHAR(12) DEFAULT ''")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS receiver_name TEXT DEFAULT ''")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS md5_hash VARCHAR(32) DEFAULT ''")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS signed_at TIMESTAMP")
        op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS countersigned_at TIMESTAMP")
    else:
        # SQLite — add columns one by one (no IF NOT EXISTS support)
        for col_name, col_type, default in [
            ("contract_id", "INTEGER", None),
            ("doc_type", "VARCHAR(20)", "'invoice'"),
            ("edo_status", "VARCHAR(30)", "'draft'"),
            ("share_uuid", "VARCHAR(36)", None),
            ("sender_user_id", "BIGINT", None),
            ("receiver_bin", "VARCHAR(12)", "''"),
            ("receiver_name", "TEXT", "''"),
            ("md5_hash", "VARCHAR(32)", "''"),
            ("signed_at", "TIMESTAMP", None),
            ("countersigned_at", "TIMESTAMP", None),
        ]:
            try:
                default_clause = f" DEFAULT {default}" if default else ""
                op.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type}{default_clause}")
            except Exception:
                pass  # Column may already exist


def downgrade() -> None:
    op.drop_table("document_shares")
    op.drop_table("esf_records")
    op.drop_table("signing_sessions")
    op.drop_table("signatures")
    op.drop_table("contracts")
    # Note: We don't drop the columns from documents to avoid data loss
