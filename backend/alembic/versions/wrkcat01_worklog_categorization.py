"""WRK/CAT additions; preserve all existing ticket and catalogue data."""
import sqlalchemy as sa
from alembic import op

revision = 'wrkcat01'
down_revision = 'r2_lifecycle'
branch_labels = depends_on = None


def upgrade():
    op.add_column('ticket', sa.Column('root_cause_detail', sa.Text(), nullable=True))
    op.create_table('ticket_worklog',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False), sa.Column('body', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(50)),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("kind IN ('internal_note','public_reply')", name='ck_worklog_kind'),
        sa.CheckConstraint("(kind = 'internal_note' AND channel IS NULL) OR (kind = 'public_reply' AND channel IS NOT NULL)", name='ck_worklog_channel'))
    op.create_table('ticket_audit',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), nullable=False),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event', sa.String(50), nullable=False), sa.Column('changes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_table('ticket_tag',
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), primary_key=True),
        sa.Column('name', sa.String(64), primary_key=True))
    op.create_index('ix_ticket_tag_name', 'ticket_tag', ['name'])
    op.create_table('category_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('axis', sa.String(32), nullable=False), sa.Column('option_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_category_usage_user_id', 'category_usage', ['user_id'])
    for table in ('ticket_worklog', 'ticket_audit'):
        op.create_index(f'ix_{table}_ticket_id', table, ['ticket_id'])


def downgrade():
    for table in ('category_usage', 'ticket_tag', 'ticket_audit', 'ticket_worklog'):
        op.drop_table(table)
    op.drop_column('ticket', 'root_cause_detail')
