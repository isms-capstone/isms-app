"""Persist SLA intervals and lifecycle reasons."""
import sqlalchemy as sa
from alembic import op

revision = "sla01_clock"
down_revision = "escsim01_merge"


def upgrade():
    op.create_table(
        "sla_clock",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("ticket.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime()),
    )
    op.create_index("ix_sla_clock_ticket_id", "sla_clock", ["ticket_id"])
    op.add_column("ticket", sa.Column("pending_customer_reason", sa.Text()))
    op.add_column("ticket", sa.Column("sla_breach_reason", sa.Text()))
    op.add_column("ticket", sa.Column("sla_exam_base_severity", sa.String(2)))


def downgrade():
    op.drop_column("ticket", "sla_exam_base_severity")
    op.drop_column("ticket", "sla_breach_reason")
    op.drop_column("ticket", "pending_customer_reason")
    op.drop_table("sla_clock")
