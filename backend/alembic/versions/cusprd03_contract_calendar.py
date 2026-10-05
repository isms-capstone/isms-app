"""P1-CUSPRD-03 customer contracts and UTC exam windows."""
from alembic import op
import sqlalchemy as sa

revision = "cusprd03"
down_revision = "cusprd05"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("organization") as batch:
        batch.add_column(sa.Column("contract_start_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("contract_end_date", sa.Date(), nullable=True))
        batch.create_check_constraint("ck_organization_contract_range",
            "contract_start_date IS NULL OR contract_end_date IS NULL OR contract_end_date >= contract_start_date")
    op.create_table("exam_window",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id", "department_id"], ["department.organization_id", "department.id"],
                                name="fk_exam_window_department_org"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_exam_window_range"))
    op.create_index("ix_exam_window_organization_id", "exam_window", ["organization_id"])
    op.create_index("ix_exam_window_starts_at", "exam_window", ["starts_at"])


def downgrade():
    op.drop_table("exam_window")
    with op.batch_alter_table("organization") as batch:
        batch.drop_constraint("ck_organization_contract_range", type_="check")
        batch.drop_column("contract_end_date")
        batch.drop_column("contract_start_date")
