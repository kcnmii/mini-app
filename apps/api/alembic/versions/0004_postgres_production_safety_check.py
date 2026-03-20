"""postgres production safety check

Revision ID: 96329df61aa2
Revises: c96c3feafed7
Create Date: 2026-03-20 17:10:19.107375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_postgres_safety'
down_revision: Union[str, None] = '0003_auto_add_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS bin_iin TEXT DEFAULT ''")
        op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS address TEXT DEFAULT ''")
        op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS director TEXT DEFAULT ''")
        
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS client_id INTEGER")
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS client_name TEXT DEFAULT ''")
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS client_bin TEXT DEFAULT ''")
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS deal_reference TEXT DEFAULT ''")
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft'")
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS due_date TIMESTAMP")

def downgrade() -> None:
    pass
