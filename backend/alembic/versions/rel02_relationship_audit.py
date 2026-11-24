"""Preserve moved worklog origin and index searchable audit history."""

import sqlalchemy as sa
from alembic import op

revision = "rel02_relationship_audit"
down_revision = "rel01_typed_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ticket_worklogs") as batch:
        batch.add_column(sa.Column("original_ticket_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_worklog_original_ticket", "ticket", ["original_ticket_id"], ["id"]
        )
        batch.create_index(
            "ix_ticket_worklogs_original_ticket_id", ["original_ticket_id"]
        )
    op.create_index(
        "ix_ticket_audit_created_at_id", "ticket_audit", ["created_at", "id"]
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM ticket_worklogs WHERE original_ticket_id IS NOT NULL LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError(
            "Downgrade would discard the original case of moved worklogs"
        )
    op.drop_index("ix_ticket_audit_created_at_id", table_name="ticket_audit")
    with op.batch_alter_table("ticket_worklogs") as batch:
        batch.drop_constraint("fk_worklog_original_ticket", type_="foreignkey")
        batch.drop_index("ix_ticket_worklogs_original_ticket_id")
        batch.drop_column("original_ticket_id")
