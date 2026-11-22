"""Add relationship types while preserving existing SIM links as related."""

import sqlalchemy as sa
from alembic import op

revision = "rel01_typed_links"
down_revision = "escsim01_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ticket_link") as batch:
        batch.add_column(
            sa.Column(
                "relationship_type",
                sa.String(16),
                nullable=False,
                server_default="related",
            )
        )
        batch.create_unique_constraint(
            "uq_ticket_link_pair_type",
            ["ticket_id", "related_ticket_id", "relationship_type"],
        )
        batch.drop_constraint("uq_ticket_link_pair", type_="unique")
        batch.create_check_constraint(
            "ck_ticket_link_type",
            "relationship_type IN ('duplicate', 'related', 'follow-up', 'caused-by', 'child-of')",
        )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM ticket_link WHERE relationship_type <> 'related' LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError("Downgrade would discard typed case relationships")
    with op.batch_alter_table("ticket_link") as batch:
        batch.create_unique_constraint(
            "uq_ticket_link_pair", ["ticket_id", "related_ticket_id"]
        )
        batch.drop_constraint("uq_ticket_link_pair_type", type_="unique")
        batch.drop_constraint("ck_ticket_link_type", type_="check")
        batch.drop_column("relationship_type")
