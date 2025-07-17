"""Add bookmarks table

Revision ID: e7f8g9h0i1j2
Revises: d6e7f8g9h0i1
Create Date: 2025-07-17 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'd6e7f8g9h0i1'
branch_labels = None
depends_on = None


def upgrade():
    # Create tbl_bookmarks table
    op.create_table('tbl_bookmarks',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('bookmark_type', sa.String(length=50), nullable=False),
        sa.Column('reference', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['tbl_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create unique constraint to prevent duplicate bookmarks per user
    op.create_index('idx_bookmarks_user_type_reference', 'tbl_bookmarks', ['user_id', 'bookmark_type', 'reference'], unique=True)
    
    # Create index for faster queries by user_id
    op.create_index('idx_bookmarks_user_id', 'tbl_bookmarks', ['user_id'])
    
    # Create index for faster queries by created_at for ordering
    op.create_index('idx_bookmarks_created_at', 'tbl_bookmarks', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_bookmarks_created_at', table_name='tbl_bookmarks')
    op.drop_index('idx_bookmarks_user_id', table_name='tbl_bookmarks')
    op.drop_index('idx_bookmarks_user_type_reference', table_name='tbl_bookmarks')
    
    # Drop table
    op.drop_table('tbl_bookmarks')