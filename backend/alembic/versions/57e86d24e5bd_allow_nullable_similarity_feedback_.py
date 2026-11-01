
"""allow nullable similarity feedback ticket

Revision ID: 57e86d24e5bd
Revises: s3_sim_v1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '57e86d24e5bd'
down_revision: Union[str, Sequence[str], None] = 's3_sim_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'similarity_feedback',
        'ticket_id',
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'similarity_feedback',
        'ticket_id',
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
