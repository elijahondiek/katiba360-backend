"""Update read_time_minutes to float

Revision ID: b3c4d5e6f7g8
Revises: a2b5c3d4e5f6
Create Date: 2025-07-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7g8'
down_revision = 'a2b5c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Change read_time_minutes from INTEGER to FLOAT
    op.alter_column('tbl_user_reading_progress', 'read_time_minutes',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False,
               existing_server_default=sa.text('0'))


def downgrade():
    # Change read_time_minutes from FLOAT back to INTEGER
    op.alter_column('tbl_user_reading_progress', 'read_time_minutes',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False,
               existing_server_default=sa.text('0'))