
"""allow nullable similarity feedback ticket id

Revision ID: 68f515e21d57
Revises: 57e86d24e5bd
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '68f515e21d57'
down_revision: Union[str, Sequence[str], None] = '57e86d24e5bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'similarity_feedback',
        'ticket_id',
        existing_type=mysql.INTEGER(display_width=11),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'similarity_feedback',
        'ticket_id',
        existing_type=mysql.INTEGER(display_width=11),
        existing_nullable=True,
        nullable=False,
    )
