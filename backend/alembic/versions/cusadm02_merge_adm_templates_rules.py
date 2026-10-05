"""Join existing CAP/CUS registry and ADM templates/rules histories.

No schema changes: retain both branches' migrations and data.
"""

revision = 'cusadm02'
down_revision = ('cap01', 'e3f4a5b6c7d8')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
