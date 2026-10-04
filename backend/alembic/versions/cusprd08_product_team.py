"""P1-CUSPRD-08 default team uses existing INFRA team registry."""
from alembic import op
import sqlalchemy as sa

revision = "cusprd08"
down_revision = "cusprd03"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("product") as batch:
        batch.add_column(sa.Column("default_team_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_product_default_team", "teams", ["default_team_id"], ["id"])
        batch.create_index("ix_product_default_team_id", ["default_team_id"])


def downgrade():
    with op.batch_alter_table("product") as batch:
        batch.drop_index("ix_product_default_team_id")
        batch.drop_constraint("fk_product_default_team", type_="foreignkey")
        batch.drop_column("default_team_id")
