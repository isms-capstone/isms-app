"""add channel to ticket_worklogs

Revision ID: 7abf1b4bce51
Revises: 6a7d84bc75bf
Create Date: 2026-11-02 19:16:43.706702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7abf1b4bce51'
down_revision: Union[str, Sequence[str], None] = '6a7d84bc75bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

def upgrade() -> None:
    op.add_column('ticket_worklogs', sa.Column('channel', sa.String(length=50), nullable=True, server_default='portal'))

def downgrade() -> None:
    op.drop_column('ticket_worklogs', 'channel')