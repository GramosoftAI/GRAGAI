"""create document_chunks table

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-05-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Execute CREATE EXTENSION IF NOT EXISTS vector;
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create the document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('kb_id', sa.UUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['kb_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_chunks_kb_id', 'document_chunks', ['kb_id'], unique=False)
    op.create_index('ix_chunks_tenant_id', 'document_chunks', ['tenant_id'], unique=False)
    op.create_index('ix_document_chunks_id', 'document_chunks', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_document_chunks_id', table_name='document_chunks')
    op.drop_index('ix_chunks_tenant_id', table_name='document_chunks')
    op.drop_index('ix_chunks_kb_id', table_name='document_chunks')
    op.drop_table('document_chunks')
    op.execute('DROP EXTENSION IF EXISTS vector')
