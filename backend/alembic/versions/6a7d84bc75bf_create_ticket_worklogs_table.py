"""create ticket_worklogs table

Revision ID: 6a7d84bc75bf
Revises: r2_lifecycle
Create Date: 2026-11-02 17:26:04.601982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6a7d84bc75bf'
down_revision: Union[str, Sequence[str], None] = 'r2_lifecycle'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ticket_worklogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['ticket.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_worklogs_ticket_id'), 'ticket_worklogs', ['ticket_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ticket_worklogs_ticket_id'), table_name='ticket_worklogs')
    op.drop_table('ticket_worklogs')
