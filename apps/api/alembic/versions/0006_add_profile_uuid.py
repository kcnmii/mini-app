"""add profile_uuid to supplier_profile

Revision ID: 0006_add_profile_uuid
Revises: 0005_edo_tables
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_add_profile_uuid'
down_revision = '0005_edo_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile_uuid column (nullable, unique, indexed)
    with op.batch_alter_table('supplier_profile', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_uuid', sa.String(36), nullable=True))
        batch_op.create_index('ix_supplier_profile_profile_uuid', ['profile_uuid'], unique=True)
    
    # Auto-generate UUIDs for existing profiles
    import uuid
    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id FROM supplier_profile WHERE profile_uuid IS NULL")).fetchall()
    for row in profiles:
        new_uuid = str(uuid.uuid4())
        conn.execute(
            sa.text("UPDATE supplier_profile SET profile_uuid = :uuid WHERE id = :id"),
            {"uuid": new_uuid, "id": row[0]}
        )


def downgrade() -> None:
    with op.batch_alter_table('supplier_profile', schema=None) as batch_op:
        batch_op.drop_index('ix_supplier_profile_profile_uuid')
        batch_op.drop_column('profile_uuid')
