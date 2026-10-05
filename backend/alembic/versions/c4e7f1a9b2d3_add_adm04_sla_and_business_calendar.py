"""add ADM-04 SLA policies and business calendar

Revision ID: c4e7f1a9b2d3
Revises: 8d2c4a1b7e90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4e7f1a9b2d3"
down_revision: Union[str, Sequence[str], None] = "8d2c4a1b7e90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sla_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sla_policies_id", "sla_policies", ["id"])
    op.create_index("ix_sla_policies_name", "sla_policies", ["name"], unique=True)
    op.create_index("ix_sla_policies_is_active", "sla_policies", ["is_active"])

    op.create_table(
        "sla_policy_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sla_policy_id", sa.Integer(), sa.ForeignKey("sla_policies.id"), nullable=False),
        sa.Column("severity", sa.String(length=2), nullable=False),
        sa.Column("first_response_value", sa.Integer(), nullable=False),
        sa.Column("first_response_unit", sa.String(length=20), nullable=False),
        sa.Column("resolution_min_value", sa.Integer(), nullable=False),
        sa.Column("resolution_max_value", sa.Integer(), nullable=False),
        sa.Column("resolution_unit", sa.String(length=20), nullable=False),
        sa.Column("business_hours_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sla_policy_id", "severity", name="uq_sla_policy_rules_policy_severity"),
    )
    op.create_index("ix_sla_policy_rules_id", "sla_policy_rules", ["id"])
    op.create_index("ix_sla_policy_rules_sla_policy_id", "sla_policy_rules", ["sla_policy_id"])
    op.create_index("ix_sla_policy_rules_severity", "sla_policy_rules", ["severity"])
    op.create_index("ix_sla_policy_rules_is_active", "sla_policy_rules", ["is_active"])

    op.create_table(
        "business_calendars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Bangkok"),
        sa.Column("work_start_time", sa.Time(), nullable=False),
        sa.Column("work_end_time", sa.Time(), nullable=False),
        sa.Column("monday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tuesday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("wednesday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("thursday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("friday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("saturday", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sunday", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_business_calendars_id", "business_calendars", ["id"])
    op.create_index("ix_business_calendars_name", "business_calendars", ["name"], unique=True)
    op.create_index("ix_business_calendars_is_active", "business_calendars", ["is_active"])

    op.create_table(
        "business_holidays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_calendar_id", sa.Integer(), sa.ForeignKey("business_calendars.id"), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("holiday_type", sa.String(length=20), nullable=False, server_default="ANNUAL"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("business_calendar_id", "holiday_date", name="uq_business_holidays_calendar_date"),
    )
    op.create_index("ix_business_holidays_id", "business_holidays", ["id"])
    op.create_index("ix_business_holidays_business_calendar_id", "business_holidays", ["business_calendar_id"])
    op.create_index("ix_business_holidays_holiday_date", "business_holidays", ["holiday_date"])
    op.create_index("ix_business_holidays_is_active", "business_holidays", ["is_active"])


def downgrade() -> None:
    op.drop_table("business_holidays")
    op.drop_table("business_calendars")
    op.drop_table("sla_policy_rules")
    op.drop_table("sla_policies")
