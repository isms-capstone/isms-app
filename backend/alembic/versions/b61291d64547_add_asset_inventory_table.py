
"""Add asset inventory table."""

from alembic import op
import sqlalchemy as sa

revision = "b61291d64547"
down_revision = "cap05_attach_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assets",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            index=True,
        ),
        sa.Column(
            "asset_code",
            sa.String(50),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "HARDWARE",
                "SOFTWARE",
                "DATA",
                "PEOPLE",
                "SERVICE",
                name="assetcategory",
            ),
            nullable=False,
            server_default="HARDWARE",
        ),
        sa.Column(
            "confidentiality",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "integrity",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "availability",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_table("assets")
