"""merge bookmarks and content views migrations

Revision ID: 488c20dd008b
Revises: dfcb88c79658
Create Date: 2025-07-17 13:18:59.299316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '488c20dd008b'
down_revision: Union[str, None] = 'dfcb88c79658'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
