"""merge bookmarks and content views migrations

Revision ID: dfcb88c79658
Revises: e7f8g9h0i1j2, g1h2i3j4k5l6
Create Date: 2025-07-17 13:17:02.022927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfcb88c79658'
down_revision: Union[str, None] = ('e7f8g9h0i1j2', 'g1h2i3j4k5l6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
