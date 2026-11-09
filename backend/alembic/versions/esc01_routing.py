"""ESC additive state; retain all cases and identify estimated historical intervals."""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "esc01_routing"
down_revision = "r2_lifecycle"
branch_labels = depends_on = None


def fk(name, target, nullable=False, **kw):
    return sa.Column(name, sa.Integer(), sa.ForeignKey(target), nullable=nullable, **kw)


def upgrade():
    op.add_column(
        "users",
        sa.Column("default_tier", sa.Integer(), nullable=False, server_default="2"),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_available", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "ticket",
        sa.Column("routing_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "team_routing",
        fk("team_id", "teams.id", primary_key=True),
        fk("leader_id", "users.id"),
    )
    op.create_table(
        "product_tier_route",
        sa.Column("id", sa.Integer(), primary_key=True),
        fk("product_id", "products.id"),
        sa.Column("tier", sa.Integer(), nullable=False),
        fk("team_id", "teams.id"),
        sa.UniqueConstraint("product_id", "tier", name="uq_product_tier_route"),
        sa.CheckConstraint("tier IN (0,1,2)", name="ck_route_tier"),
    )
    op.create_index(
        "ix_product_tier_route_product_id", "product_tier_route", ["product_id"]
    )
    policy = op.create_table(
        "routing_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("s1_minutes", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        fk("business_calendar_id", "business_calendars.id", nullable=True),
        sa.CheckConstraint(
            "s1_minutes BETWEEN 1 AND 1440", name="ck_routing_s1_minutes"
        ),
    )
    op.bulk_insert(
        policy,
        [{"id": 1, "s1_minutes": 15, "enabled": True, "business_calendar_id": None}],
    )
    op.create_table(
        "routing_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        fk("ticket_id", "ticket.id"),
        fk("status_history_id", "ticket_status_history.id"),
        fk("actor_id", "users.id", nullable=True),
        sa.Column("kind", sa.String(30), nullable=False),
        fk("from_user_id", "users.id", nullable=True),
        fk("to_user_id", "users.id", nullable=True),
        sa.Column("from_tier", sa.Integer(), nullable=False),
        sa.Column("to_tier", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("checked", sa.Text()),
        sa.Column("requested", sa.Text()),
        fk("return_of_id", "routing_event.id", nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_routing_event_ticket_id", "routing_event", ["ticket_id"])
    op.create_table(
        "ticket_tier_interval",
        sa.Column("id", sa.Integer(), primary_key=True),
        fk("ticket_id", "ticket.id"),
        fk("open_ticket_id", "ticket.id", nullable=True, unique=True),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("entered_at", sa.DateTime(), nullable=False),
        sa.Column("exited_at", sa.DateTime()),
        fk("status_history_id", "ticket_status_history.id", nullable=True),
        sa.Column("is_estimated", sa.Boolean(), nullable=False),
        sa.CheckConstraint("tier IN (0,1,2)", name="ck_interval_tier"),
    )
    op.create_index(
        "ix_ticket_tier_interval_ticket_id", "ticket_tier_interval", ["ticket_id"]
    )
    op.create_table(
        "routing_notification",
        sa.Column("id", sa.Integer(), primary_key=True),
        fk("recipient_id", "users.id"),
        fk("ticket_id", "ticket.id"),
        sa.Column("dedupe_key", sa.String(180), nullable=False, unique=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime()),
    )
    for column in ("recipient_id", "ticket_id"):
        op.create_index(
            "ix_routing_notification_" + column, "routing_notification", [column]
        )
    lease = op.create_table(
        "routing_job_lease",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("locked_until", sa.DateTime(), nullable=False),
        sa.Column("last_success_at", sa.DateTime()),
    )
    op.bulk_insert(lease, [{"id": 1, "locked_until": datetime(1970, 1, 1)}])
    op.execute(
        "UPDATE ticket SET current_tier=2 WHERE current_tier IS NULL AND status != 'DRAFT'"
    )
    op.execute("""INSERT INTO ticket_tier_interval
        (ticket_id, open_ticket_id, tier, entered_at, exited_at, is_estimated)
        SELECT id, id, current_tier, created_at, NULL, 1 FROM ticket
        WHERE status IN ('NEW','IN_PROGRESS','PENDING_CUSTOMER','PENDING_EXTERNAL','REOPENED')""")


def downgrade():
    for table in [
        "routing_job_lease",
        "routing_notification",
        "ticket_tier_interval",
        "routing_event",
        "routing_policy",
        "product_tier_route",
        "team_routing",
    ]:
        op.drop_table(table)
    op.drop_column("ticket", "routing_version")
    op.drop_column("users", "is_available")
    op.drop_column("users", "default_tier")
