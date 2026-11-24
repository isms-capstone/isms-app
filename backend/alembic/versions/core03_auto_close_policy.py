"""CORE-03: configurable business-day delay before RESOLVED cases close automatically."""
import sqlalchemy as sa
from alembic import op

revision = "core03_auto_close_policy"
down_revision = "por_portal02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("routing_policy") as batch:
        batch.add_column(sa.Column("auto_close_business_days", sa.Integer(), nullable=False, server_default="3"))
        batch.create_check_constraint("ck_routing_auto_close_days", "auto_close_business_days BETWEEN 1 AND 30")


def downgrade() -> None:
    with op.batch_alter_table("routing_policy") as batch:
        batch.drop_constraint("ck_routing_auto_close_days", type_="check")
        batch.drop_column("auto_close_business_days")
