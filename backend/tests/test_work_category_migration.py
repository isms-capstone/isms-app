"""Upgrade a populated pre-WRK/CAT schema without rewriting merged migrations."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.api.v1.router import api_router  # noqa: F401 - register all application models
from app.db.base_class import Base


def test_populated_wrkcat_migration_round_trip():
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/wrkcat01_worklog_categorization.py'
    spec = importlib.util.spec_from_file_location('wrkcat_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine('sqlite://')
    added = {'ticket_audit', 'ticket_tag', 'category_usage'}
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=[table for table in Base.metadata.sorted_tables if table.name not in added])
        connection.exec_driver_sql('ALTER TABLE ticket DROP COLUMN root_cause_detail')
        connection.execute(text("INSERT INTO roles(id,name) VALUES(71,'Admin')"))
        connection.execute(text("INSERT INTO users(id,username,email,hashed_password,role_id,is_active,created_at,updated_at) VALUES(71,'migration','migration@example.org','unused',71,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO ticket(id,ticket_no,subject,status,created_by_id,reported_at,created_at,sla_breached,reopen_count,is_exam_window) VALUES(71,'DVHT-202611-00071','Existing merged case','CLOSED',71,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,0,2,0)"))
        original = dict(connection.execute(text('SELECT * FROM ticket WHERE id=71')).mappings().one())
        connection.execute(text("INSERT INTO ticket_worklogs(id,ticket_id,author_id,message,is_internal,channel,created_at) VALUES(71,71,71,'ข้อความเดิมก่อน CAT',1,'phone',CURRENT_TIMESTAMP)"))
        old_worklog = dict(connection.execute(text('SELECT * FROM ticket_worklogs WHERE id=71')).mappings().one())
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        current = dict(connection.execute(text('SELECT * FROM ticket WHERE id=71')).mappings().one())
        assert current.pop('root_cause_detail') is None
        assert current == original
        assert dict(connection.execute(text('SELECT * FROM ticket_worklogs WHERE id=71')).mappings().one()) == old_worklog
        assert 'ticket_worklog' not in inspect(connection).get_table_names()
        inspector = inspect(connection)
        for table in added:
            assert {column['name'] for column in inspector.get_columns(table)} == set(Base.metadata.tables[table].columns.keys())
        assert 'ticket_worklogs' in inspector.get_table_names()
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []
        migration.downgrade()
        assert not added.intersection(inspect(connection).get_table_names())
        assert dict(connection.execute(text('SELECT * FROM ticket WHERE id=71')).mappings().one()) == original
        assert dict(connection.execute(text('SELECT * FROM ticket_worklogs WHERE id=71')).mappings().one()) == old_worklog
        migration.upgrade()
        assert added.issubset(inspect(connection).get_table_names())
    engine.dispose()
