"""add ADM-02 master data phase 1

Revision ID: 8d2c4a1b7e90
Revises: fef2a1063bc1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8d2c4a1b7e90"
down_revision: Union[str, Sequence[str], None] = "fef2a1063bc1"
branch_labels = None
depends_on = None


def _common_columns():
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table("products", *_common_columns())
    op.create_index("ix_products_id", "products", ["id"])
    op.create_index("ix_products_name", "products", ["name"], unique=True)
    op.create_index("ix_products_is_active", "products", ["is_active"])

    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("product_id", "name", name="uq_modules_product_name"),
    )
    op.create_index("ix_modules_id", "modules", ["id"])
    op.create_index("ix_modules_product_id", "modules", ["product_id"])
    op.create_index("ix_modules_is_active", "modules", ["is_active"])

    op.create_table(
        "problem_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_id", sa.Integer(), sa.ForeignKey("modules.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("module_id", "name", name="uq_problem_types_module_name"),
    )
    op.create_index("ix_problem_types_id", "problem_types", ["id"])
    op.create_index("ix_problem_types_module_id", "problem_types", ["module_id"])
    op.create_index("ix_problem_types_is_active", "problem_types", ["is_active"])

    for table in ("symptoms", "service_stages"):
        columns = [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("name", sa.String(length=150 if table == "symptoms" else 100), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("product_id", "name", name=f"uq_{table}_product_name"),
        ]
        if table == "service_stages":
            columns.insert(4, sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        op.create_table(table, *columns)
        op.create_index(f"ix_{table}_id", table, ["id"])
        op.create_index(f"ix_{table}_product_id", table, ["product_id"])
        op.create_index(f"ix_{table}_is_active", table, ["is_active"])

    for table in ("ticket_types",):
        op.create_table(table, *_common_columns())
        op.create_index(f"ix_{table}_id", table, ["id"])
        op.create_index(f"ix_{table}_name", table, ["name"], unique=True)
        op.create_index(f"ix_{table}_is_active", table, ["is_active"])

    for table in ("cause_codes", "solution_codes"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(f"ix_{table}_id", table, ["id"])
        op.create_index(f"ix_{table}_code", table, ["code"], unique=True)
        op.create_index(f"ix_{table}_is_active", table, ["is_active"])


def downgrade() -> None:
    for table in ("solution_codes", "cause_codes", "ticket_types", "service_stages", "symptoms", "problem_types", "modules", "products"):
        op.drop_table(table)
