"""Alembic script template"""
"""Add dataset_schema and row_data GIN index

Revision ID: f6a7fd0e3869
Revises: 371977a11f9a
Create Date: 2026-06-25 16:56:26.121380

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f6a7fd0e3869'
down_revision = '371977a11f9a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_tablerows_row_data_gin', 'document_table_rows', ['row_data'], unique=False, postgresql_using='gin')
    op.add_column('knowledge_bases', sa.Column('dataset_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('knowledge_bases', 'dataset_schema')
    op.drop_index('ix_tablerows_row_data_gin', table_name='document_table_rows', postgresql_using='gin')
