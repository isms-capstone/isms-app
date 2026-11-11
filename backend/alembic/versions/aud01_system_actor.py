"""Allow automated ticket changes to record a system actor."""
from alembic import op
import sqlalchemy as sa

revision = 'aud01_system_actor'
down_revision = 'escsim01_merge'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ticket_audit') as batch:
        batch.alter_column('actor_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT COUNT(*) FROM ticket_audit WHERE actor_id IS NULL')):
        raise RuntimeError('Downgrade would lose system actor information')
    with op.batch_alter_table('ticket_audit') as batch:
        batch.alter_column('actor_id', existing_type=sa.Integer(), nullable=False)
