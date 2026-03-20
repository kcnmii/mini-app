"""drop bank_transactions table

We no longer store raw bank statement rows.
Instead, the 1C parser processes everything in memory and only
creates Payment records for matched invoices.

Revision ID: 0002_drop_bank_transactions
Revises: 0001_baseline
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_drop_bank_transactions"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bank_transactions")


def downgrade() -> None:
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
