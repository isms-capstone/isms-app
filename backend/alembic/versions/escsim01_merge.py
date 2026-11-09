"""Join the ESC and SIM/WRK/CAT migration histories."""

revision = "escsim01_merge"
down_revision = ("esc01_routing", "simwrk02_latest")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
