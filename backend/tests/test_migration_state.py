import pytest
from sqlalchemy import create_engine, inspect, text

from app.db.migration_state import check_migration_history, migration_scripts, require_current_schema
from app.db.init_db import init_db
from sqlalchemy.orm import Session


def test_unmigrated_startup_never_creates_tables():
    engine = create_engine('sqlite://')
    with engine.connect() as connection:
        assert check_migration_history(connection) == ()
    with Session(engine) as db:
        with pytest.raises(RuntimeError, match='migrations are pending'):
            init_db(db)
    assert inspect(engine).get_table_names() == []
    engine.dispose()


def test_existing_unmanaged_schema_is_blocked_and_revisions_checked():
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE legacy_data (id INTEGER PRIMARY KEY)'))
        with pytest.raises(RuntimeError, match='no Alembic revision'):
            check_migration_history(connection)
        connection.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)'))
        connection.execute(text("INSERT INTO alembic_version VALUES ('fef2a1063bc1')"))
        with pytest.raises(RuntimeError, match='migrations are pending'):
            require_current_schema(connection)
        connection.execute(text('DELETE FROM alembic_version'))
        connection.execute(text('INSERT INTO alembic_version VALUES (:revision)'),
                           {'revision': migration_scripts().get_current_head()})
        require_current_schema(connection)
        assert set(inspect(connection).get_table_names()) == {'legacy_data', 'alembic_version'}
    engine.dispose()
