"""Add CAP-05 case attachments."""
from alembic import op
import sqlalchemy as sa

revision = "cap05_attach_001"
down_revision = "cusadm02"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "ticket_attachment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("ticket.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ticket_attachment_ticket_id", "ticket_attachment", ["ticket_id"])

def downgrade():
    op.drop_index("ix_ticket_attachment_ticket_id", table_name="ticket_attachment")
    op.drop_table("ticket_attachment")
