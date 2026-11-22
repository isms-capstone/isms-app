"""Persist saved views and export audit, and backfill the Thai case index."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import VARCHAR

from app.services.case_search_index import token_rows

revision = 'sea01_case_search'
down_revision = 'aud01_system_actor'
branch_labels = None
depends_on = None


def upgrade():
    token_table = op.create_table(
        'case_search_token',
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('ticket.id'), primary_key=True),
        sa.Column('source_id', sa.Integer(), primary_key=True),
        sa.Column('token', sa.String(191).with_variant(
            VARCHAR(191, charset='utf8mb4', collation='utf8mb4_bin'), 'mysql', 'mariadb'), primary_key=True),
    )
    op.create_index('ix_case_search_token_lookup', 'case_search_token', ['token', 'ticket_id'])
    op.create_table(
        'case_search_view',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id')),
        sa.Column('filters', sa.JSON(), nullable=False),
    )
    op.create_index('ix_case_search_view_owner_id', 'case_search_view', ['owner_id'])
    op.create_index('ix_case_search_view_team_id', 'case_search_view', ['team_id'])
    op.create_table(
        'case_export_audit',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('format', sa.String(4), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=False),
        sa.Column('ticket_ids', sa.JSON(), nullable=False),
    )
    op.create_index('ix_case_export_audit_actor_id', 'case_export_audit', ['actor_id'])

    connection = op.get_bind()
    for table, columns in (('ticket', 'id, subject, description'),
                           ('ticket_worklogs', 'id, ticket_id, message')):
        last_id = 0
        while True:
            rows = connection.execute(sa.text(
                f'SELECT {columns} FROM {table} WHERE id > :last_id ORDER BY id LIMIT 500'
            ), {'last_id': last_id}).mappings().all()
            if not rows:
                break
            for row in rows:
                if table == 'ticket':
                    terms = token_rows(row['id'], 0, f"{row['subject'] or ''} {row['description'] or ''}")
                else:
                    terms = token_rows(row['ticket_id'], row['id'], row['message'])
                if terms:
                    connection.execute(token_table.insert(), terms)
            last_id = rows[-1]['id']


def downgrade():
    op.drop_table('case_export_audit')
    op.drop_table('case_search_view')
    op.drop_table('case_search_token')
