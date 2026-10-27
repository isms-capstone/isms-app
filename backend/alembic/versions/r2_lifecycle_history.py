"""Persist lifecycle context and audit without rewriting existing case data."""
from alembic import op
import sqlalchemy as sa

revision = 'r2_lifecycle'
down_revision = 'b61291d64547'
branch_labels = depends_on = None


def upgrade():
    op.add_column('ticket', sa.Column('pending_external_reason', sa.Text(), nullable=True))
    op.add_column('ticket', sa.Column('cancel_reason', sa.Text(), nullable=True))
    op.create_table('ticket_status_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), nullable=False),
        sa.Column('from_status', sa.String(24), nullable=False),
        sa.Column('to_status', sa.String(24), nullable=False),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False))
    op.create_index('ix_ticket_status_history_ticket_id', 'ticket_status_history', ['ticket_id'])


def downgrade():
    op.drop_table('ticket_status_history')
    op.drop_column('ticket', 'cancel_reason')
    op.drop_column('ticket', 'pending_external_reason')
