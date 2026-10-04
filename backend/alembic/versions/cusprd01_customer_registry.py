"""P1-CUSPRD-01 customer registry.

Revision ID: cusprd01
Revises: fef2a1063bc1
"""
from alembic import op
import sqlalchemy as sa

revision = "cusprd01"
down_revision = "fef2a1063bc1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("organization", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("name", sa.String(255), nullable=False),
                    sa.Column("is_active", sa.Boolean(), nullable=False))
    op.create_index("ix_organization_name", "organization", ["name"])
    op.create_table("contact", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
                    sa.Column("name", sa.String(255), nullable=False),
                    sa.Column("is_active", sa.Boolean(), nullable=False))
    op.create_index("ix_contact_name", "contact", ["name"])
    op.create_index("ix_contact_organization_id", "contact", ["organization_id"])
    op.create_table("channel_identity", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contact.id"), nullable=False),
                    sa.Column("channel_type", sa.String(20), nullable=False),
                    sa.Column("value", sa.String(255), nullable=False),
                    sa.UniqueConstraint("contact_id", "channel_type", "value", name="uq_contact_channel"),
                    sa.CheckConstraint("channel_type IN ('line_user_id', 'line_group_id', 'email', 'phone')", name="ck_channel_type"))
    op.create_index("ix_channel_identity_contact_id", "channel_identity", ["contact_id"])
    op.create_index("ix_channel_identity_value", "channel_identity", ["value"])


def downgrade():
    op.drop_table("channel_identity")
    op.drop_table("contact")
    op.drop_table("organization")
