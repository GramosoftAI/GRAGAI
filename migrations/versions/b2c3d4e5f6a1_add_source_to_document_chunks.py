"""add source to document_chunks

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-25 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable source column to document_chunks
    op.add_column('document_chunks', sa.Column('source', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove source column from document_chunks
    op.drop_column('document_chunks', 'source')
