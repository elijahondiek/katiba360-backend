"""Add content views table for analytics

Revision ID: g1h2i3j4k5l6
Revises: f9g0h1i2j3k4
Create Date: 2024-07-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f9g0h1i2j3k4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the content_views table
    op.create_table(
        'tbl_content_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('content_reference', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, default=1),
        sa.Column('first_viewed_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('now()')),
        sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('now()')),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['tbl_users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for performance
    op.create_index('idx_content_views_content_type', 'tbl_content_views', ['content_type'])
    op.create_index('idx_content_views_content_reference', 'tbl_content_views', ['content_reference'])
    op.create_index('idx_content_views_user_id', 'tbl_content_views', ['user_id'])
    op.create_index('idx_content_views_last_viewed_at', 'tbl_content_views', ['last_viewed_at'])
    op.create_index('idx_content_views_first_viewed_at', 'tbl_content_views', ['first_viewed_at'])
    
    # Composite indexes for common queries
    op.create_index('idx_content_views_type_ref', 'tbl_content_views', ['content_type', 'content_reference'])
    op.create_index('idx_content_views_type_user', 'tbl_content_views', ['content_type', 'user_id'])
    op.create_index('idx_content_views_user_viewed', 'tbl_content_views', ['user_id', 'last_viewed_at'])
    
    # Unique constraint for user-specific content views (to avoid duplicate entries)
    op.create_index('idx_content_views_user_content_unique', 'tbl_content_views', 
                   ['user_id', 'content_type', 'content_reference'], unique=True,
                   postgresql_where=sa.text('user_id IS NOT NULL'))


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_content_views_user_content_unique', table_name='tbl_content_views')
    op.drop_index('idx_content_views_user_viewed', table_name='tbl_content_views')
    op.drop_index('idx_content_views_type_user', table_name='tbl_content_views')
    op.drop_index('idx_content_views_type_ref', table_name='tbl_content_views')
    op.drop_index('idx_content_views_first_viewed_at', table_name='tbl_content_views')
    op.drop_index('idx_content_views_last_viewed_at', table_name='tbl_content_views')
    op.drop_index('idx_content_views_user_id', table_name='tbl_content_views')
    op.drop_index('idx_content_views_content_reference', table_name='tbl_content_views')
    op.drop_index('idx_content_views_content_type', table_name='tbl_content_views')
    
    # Drop the table
    op.drop_table('tbl_content_views')