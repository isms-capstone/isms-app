"""WRK/CAT additions; preserve all existing ticket and catalogue data."""
import sqlalchemy as sa
from alembic import op

revision = 'wrkcat01'
down_revision = '7abf1b4bce51'
branch_labels = depends_on = None


def upgrade():
    op.add_column('ticket', sa.Column('root_cause_detail', sa.Text(), nullable=True))
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
    for table in ('ticket_audit',):
        op.create_index(f'ix_{table}_ticket_id', table, ['ticket_id'])


def downgrade():
    for table in ('category_usage', 'ticket_tag', 'ticket_audit'):
        op.drop_table(table)
    op.drop_column('ticket', 'root_cause_detail')
