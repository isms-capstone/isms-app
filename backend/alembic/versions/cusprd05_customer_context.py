"""P1-CUSPRD-05 reusable organization context."""
from alembic import op
import sqlalchemy as sa

revision = "cusprd05"
down_revision = "cusprd02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("department",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_key", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("organization_id", "name_key", name="uq_department_name"),
        sa.UniqueConstraint("organization_id", "id", name="uq_department_org_id"))
    op.create_index("ix_department_organization_id", "department", ["organization_id"])
    op.create_table("course_or_exam",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_key", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("organization_id", "kind", "name_key", name="uq_course_exam_name"),
        sa.CheckConstraint("kind IN ('course', 'exam')", name="ck_course_exam_kind"))
    op.create_index("ix_course_or_exam_organization_id", "course_or_exam", ["organization_id"])


def downgrade():
    op.drop_table("course_or_exam")
    op.drop_table("department")
