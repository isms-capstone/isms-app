"""Read-only schema checks used before migration and before application seeding."""
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect


def migration_scripts():
    return ScriptDirectory.from_config(Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini')))


def check_migration_history(connection):
    scripts = migration_scripts()
    heads = MigrationContext.configure(connection).get_current_heads()
    tables = set(inspect(connection).get_table_names()) - {'alembic_version'}
    if tables and not heads:
        raise RuntimeError('Existing database has tables but no Alembic revision. Review its schema and backup before migration; do not stamp automatically.')
    for revision in heads:
        if scripts.get_revision(revision) is None:
            raise RuntimeError('Database revision is not in this checkout; review before migration.')
    return heads


def require_current_schema(connection):
    heads = check_migration_history(connection)
    if set(heads) != set(migration_scripts().get_heads()):
        raise RuntimeError('Database migrations are pending. Run python -m alembic upgrade head before starting/seeding the app.')


if __name__ == '__main__':
    from app.db.session import engine
    with engine.connect() as connection:
        heads = check_migration_history(connection)
        print('Migration preflight passed. Revisions:', ', '.join(heads) or '(empty database)')
