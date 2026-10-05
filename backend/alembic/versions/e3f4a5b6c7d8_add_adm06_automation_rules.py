"""add ADM-06 automation rules

Revision ID: e3f4a5b6c7d8
Revises: d1e2f3a4b5c6
"""

from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("condition_field", sa.String(length=50), nullable=False),
        sa.Column("condition_operator", sa.String(length=20), nullable=False, server_default="eq"),
        sa.Column("condition_value", sa.String(length=100), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("action_team_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["action_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_rules_id", "automation_rules", ["id"], unique=False)
    op.create_index("ix_automation_rules_name", "automation_rules", ["name"], unique=False)
    op.create_index("ix_automation_rules_priority", "automation_rules", ["priority"], unique=False)
    op.create_index("ix_automation_rules_action_team_id", "automation_rules", ["action_team_id"], unique=False)
    op.create_index("ix_automation_rules_is_active", "automation_rules", ["is_active"], unique=False)


def downgrade() -> None:
    # Dropping the table removes its indexes and FK together. MariaDB rejects
    # dropping the action-team index while its foreign key still needs it.
    op.drop_table("automation_rules")
