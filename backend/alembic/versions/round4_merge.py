"""Join the SLA, product SSO, relationship and search/audit histories.

Each feature branch started from escsim01_merge independently. This revision
only records that all four schemas are applied; it changes no tables.
"""

revision = "round4_merge"
down_revision = ("sla01_clock", "por_sso01", "rel02_relationship_audit", "sea01_case_search")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
