"""P1-CUSPRD-02 extensible product registry.

Revision ID: cusprd02
Revises: cusprd01
"""
from alembic import op
import sqlalchemy as sa

revision = "cusprd02"
down_revision = "cusprd01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("product",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("code"))
    op.create_index("ix_product_name", "product", ["name"])
    op.create_table("product_module",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("product_id", "code", name="uq_product_module_code"))
    op.create_index("ix_product_module_product_id", "product_module", ["product_id"])
    op.create_table("product_instance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("organization_id", "product_id", "code", name="uq_org_product_instance_code"))
    op.create_index("ix_product_instance_organization_id", "product_instance", ["organization_id"])
    op.create_index("ix_product_instance_product_id", "product_instance", ["product_id"])


def downgrade():
    op.drop_table("product_instance")
    op.drop_table("product_module")
    op.drop_table("product")
