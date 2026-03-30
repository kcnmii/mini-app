"""add receiver_user_id to documents

Revision ID: 0007_add_receiver_user_id
Revises: 0006_add_profile_uuid
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_add_receiver_user_id'
down_revision = '0006_add_profile_uuid'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add receiver_user_id column (nullable, indexed)
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('receiver_user_id', sa.BigInteger(), nullable=True))
        batch_op.create_index('ix_documents_receiver_user_id', ['receiver_user_id'])


def downgrade() -> None:
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index('ix_documents_receiver_user_id')
        batch_op.drop_column('receiver_user_id')
