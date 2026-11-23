"""ADM-06: persist each case's responsible team decided by routes/automation rules."""
import sqlalchemy as sa
from alembic import op

revision = "adm06_ticket_team"
down_revision = "core03_auto_close_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ticket") as batch:
        batch.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_ticket_team_id", "teams", ["team_id"], ["id"])
        batch.create_index("ix_ticket_team_id", ["team_id"])


def downgrade() -> None:
    with op.batch_alter_table("ticket") as batch:
        batch.drop_index("ix_ticket_team_id")
        batch.drop_constraint("fk_ticket_team_id", type_="foreignkey")
        batch.drop_column("team_id")
