"""P1-CUSPRD-07: associate canonical ADM products with ADM SLA policies."""
from alembic import op
import sqlalchemy as sa

revision = "cusprd07"
down_revision = "cusadm01"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("sla_policy_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_products_sla_policy", "sla_policies", ["sla_policy_id"], ["id"])
        batch.create_index("ix_products_sla_policy_id", ["sla_policy_id"])


def downgrade():
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("fk_products_sla_policy", type_="foreignkey")
        batch.drop_index("ix_products_sla_policy_id")
        batch.drop_column("sla_policy_id")
