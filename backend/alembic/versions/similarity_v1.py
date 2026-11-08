"""SIM v1: search_text column + FULLTEXT index + similarity_feedback table."""
from alembic import op
import sqlalchemy as sa

revision = 's3_sim_v1'
down_revision = 'r2_lifecycle'   # ตรวจด้วย `alembic heads` ถ้ามี migration ใหม่กว่านี้ ให้ใช้ revision นั้นแทน
branch_labels = depends_on = None


def upgrade():
    op.add_column('ticket', sa.Column('search_text', sa.Text(), nullable=True))
    op.create_table('similarity_feedback',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), nullable=False),
        sa.Column('suggested', sa.JSON(), nullable=False),
        sa.Column('decision', sa.String(16), nullable=True),
        sa.Column('chosen_ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_similarity_feedback_ticket_id', 'similarity_feedback', ['ticket_id'])

    bind = op.get_bind()
    # ตัดคำเคสที่มีอยู่แล้วให้ค้นเจอ
    from app.services.similarity import build_search_text
    for row in bind.execute(sa.text('SELECT id, subject, description FROM ticket')).all():
        bind.execute(sa.text('UPDATE ticket SET search_text = :t WHERE id = :i'),
                     {'t': build_search_text(row.subject, row.description), 'i': row.id})
    if bind.dialect.name == 'mysql':
        op.execute('ALTER TABLE ticket ADD FULLTEXT INDEX ft_ticket_search_text (search_text)')


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        op.execute('ALTER TABLE ticket DROP INDEX ft_ticket_search_text')
    op.drop_index('ix_similarity_feedback_ticket_id', table_name='similarity_feedback')
    op.drop_table('similarity_feedback')
    op.drop_column('ticket', 'search_text')
