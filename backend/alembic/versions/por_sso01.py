"""Persist product identities and consumed intake grants."""
from alembic import op
import sqlalchemy as sa

revision = "por_sso01"
down_revision = "escsim01_merge"


def upgrade():
    op.create_table(
        "portal_identity",
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), primary_key=True),
        sa.Column("identity_key", sa.String(64), primary_key=True),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("contact.id"), nullable=False),
    )
    op.create_table(
        "portal_submission",
        sa.Column("grant_key", sa.String(64), primary_key=True),
        sa.Column("ticket_id", sa.Integer, sa.ForeignKey("ticket.id", ondelete="CASCADE"), nullable=False),
    )

    op.create_table(
        "portal_email",
        sa.Column("worklog_id", sa.Integer, sa.ForeignKey("ticket_worklogs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("recipient", sa.String(255), nullable=False),
    )


def downgrade():
    op.drop_table("portal_email")
    op.drop_table("portal_submission")
    op.drop_table("portal_identity")
