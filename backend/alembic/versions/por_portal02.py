"""Self-service portal: contact visibility, sign-in links, mail outbox, status notices (POR-07..10)."""
import sqlalchemy as sa
from alembic import op

revision = "por_portal02"
down_revision = "sla02_deadlines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contact", sa.Column("portal_scope", sa.String(16), nullable=False, server_default="own"))
    op.create_table(
        "portal_magic_link",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("contact.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime),
    )
    op.create_index("ix_portal_magic_link_contact_id", "portal_magic_link", ["contact_id"])
    op.create_index("ix_portal_magic_link_email", "portal_magic_link", ["email"])
    op.create_table(
        "portal_outbox",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "portal_announcement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticket_id", sa.Integer, sa.ForeignKey("ticket.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("resolved_at", sa.DateTime),
    )
    op.create_index("ix_portal_announcement_ticket_id", "portal_announcement", ["ticket_id"])
    op.create_index("ix_portal_announcement_is_active", "portal_announcement", ["is_active"])


def downgrade() -> None:
    op.drop_table("portal_announcement")
    op.drop_table("portal_outbox")
    op.drop_table("portal_magic_link")
    op.drop_column("contact", "portal_scope")
