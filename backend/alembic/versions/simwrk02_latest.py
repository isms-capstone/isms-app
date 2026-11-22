"""Merge SIM with the canonical WRK/CAT schema without duplicate worklog tables."""

from alembic import op
import sqlalchemy as sa

revision = "simwrk02_latest"
down_revision = ("68f515e21d57", "wrkcat01")
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table("similarity_feedback") as batch:
        batch.add_column(sa.Column("query", sa.Text(), nullable=True))
        batch.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("product_instance_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_sim_feedback_organization", "organization", ["organization_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_sim_feedback_instance",
            "product_instance",
            ["product_instance_id"],
            ["id"],
        )
    op.create_table(
        "ticket_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Integer(), sa.ForeignKey("ticket.id"), nullable=False
        ),
        sa.Column(
            "related_ticket_id",
            sa.Integer(),
            sa.ForeignKey("ticket.id"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "ticket_id", "related_ticket_id", name="uq_ticket_link_pair"
        ),
        sa.CheckConstraint(
            "ticket_id != related_ticket_id", name="ck_ticket_link_not_self"
        ),
    )
    op.create_index("ix_ticket_link_ticket_id", "ticket_link", ["ticket_id"])


def downgrade():
    op.drop_table("ticket_link")
    with op.batch_alter_table("similarity_feedback") as batch:
        batch.drop_constraint("fk_sim_feedback_instance", type_="foreignkey")
        batch.drop_constraint("fk_sim_feedback_organization", type_="foreignkey")
        batch.drop_column("product_instance_id")
        batch.drop_column("organization_id")
        batch.drop_column("query")
