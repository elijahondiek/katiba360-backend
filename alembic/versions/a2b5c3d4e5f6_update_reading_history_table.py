"""Update reading history table

Revision ID: a2b5c3d4e5f6
Revises: 5f8f7d68bd9d
Create Date: 2025-05-14 20:40:18.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a2b5c3d4e5f6'
down_revision = '5f8f7d68bd9d'
branch_labels = None
depends_on = None


def upgrade():
    # Change content_id from UUID to String
    op.alter_column('tbl_reading_history', 'content_id',
               existing_type=postgresql.UUID(),
               type_=sa.String(length=255),
               existing_nullable=False)
    
    # Add new columns
    op.add_column('tbl_reading_history', sa.Column('time_spent_seconds', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tbl_reading_history', sa.Column('position', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('tbl_reading_history', sa.Column('total_length', sa.Float(), nullable=False, server_default='1.0'))
    op.add_column('tbl_reading_history', sa.Column('read_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Change progress_percentage from Integer to Float
    op.alter_column('tbl_reading_history', 'progress_percentage',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False,
               existing_server_default=sa.text('0'))


def downgrade():
    # Change progress_percentage back to Integer
    op.alter_column('tbl_reading_history', 'progress_percentage',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False,
               existing_server_default=sa.text('0'))
    
    # Drop new columns
    op.drop_column('tbl_reading_history', 'read_at')
    op.drop_column('tbl_reading_history', 'total_length')
    op.drop_column('tbl_reading_history', 'position')
    op.drop_column('tbl_reading_history', 'time_spent_seconds')
    
    # Change content_id back to UUID
    op.alter_column('tbl_reading_history', 'content_id',
               existing_type=sa.String(length=255),
               type_=postgresql.UUID(),
               existing_nullable=False)
