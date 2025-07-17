"""Add reading_time_minutes to reading history

Revision ID: d6e7f8g9h0i1
Revises: c5d6e7f8g9h0
Create Date: 2025-07-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd6e7f8g9h0i1'
down_revision = 'c5d6e7f8g9h0'
branch_labels = None
depends_on = None


def upgrade():
    # Add reading_time_minutes column to tbl_reading_history
    op.add_column('tbl_reading_history', sa.Column('reading_time_minutes', sa.Float(), nullable=False, server_default='0.0'))


def downgrade():
    # Drop reading_time_minutes column from tbl_reading_history
    op.drop_column('tbl_reading_history', 'reading_time_minutes')