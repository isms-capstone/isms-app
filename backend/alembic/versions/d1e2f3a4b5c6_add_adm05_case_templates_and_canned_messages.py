"""add case templates and canned messages for ADM-02

Revision ID: d1e2f3a4b5c6
Revises: c4e7f1a9b2d3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c4e7f1a9b2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("module_id", sa.Integer(), sa.ForeignKey("modules.id"), nullable=False),
        sa.Column("problem_type_id", sa.Integer(), sa.ForeignKey("problem_types.id"), nullable=False),
        sa.Column("default_severity", sa.String(length=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_case_templates_id", "case_templates", ["id"])
    op.create_index("ix_case_templates_name", "case_templates", ["name"], unique=True)
    op.create_index("ix_case_templates_product_id", "case_templates", ["product_id"])
    op.create_index("ix_case_templates_module_id", "case_templates", ["module_id"])
    op.create_index("ix_case_templates_problem_type_id", "case_templates", ["problem_type_id"])
    op.create_index("ix_case_templates_default_severity", "case_templates", ["default_severity"])
    op.create_index("ix_case_templates_is_active", "case_templates", ["is_active"])

    op.create_table(
        "canned_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("message", sa.String(length=5000), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_canned_messages_id", "canned_messages", ["id"])
    op.create_index("ix_canned_messages_name", "canned_messages", ["name"], unique=True)
    op.create_index("ix_canned_messages_is_active", "canned_messages", ["is_active"])


def downgrade() -> None:
    op.drop_table("canned_messages")
    op.drop_table("case_templates")
