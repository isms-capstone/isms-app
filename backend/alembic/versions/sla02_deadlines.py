"""Store SLA risk/due times so queues can filter and sort in SQL.

Values are derived data. The routing worker recalculates every monitored case
on its next five-minute cycle, so existing cases are filled without a backfill
here; until then they sort after cases that already have a due time.
"""
import sqlalchemy as sa
from alembic import op

revision = "sla02_deadlines"
down_revision = "round4_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket", sa.Column("sla_due_at", sa.DateTime(), nullable=True))
    op.add_column("ticket", sa.Column("sla_risk_at", sa.DateTime(), nullable=True))
    op.create_index("ix_ticket_sla_due_at", "ticket", ["sla_due_at"])
    op.create_index("ix_ticket_sla_risk_at", "ticket", ["sla_risk_at"])


def downgrade() -> None:
    op.drop_index("ix_ticket_sla_risk_at", table_name="ticket")
    op.drop_index("ix_ticket_sla_due_at", table_name="ticket")
    op.drop_column("ticket", "sla_risk_at")
    op.drop_column("ticket", "sla_due_at")
