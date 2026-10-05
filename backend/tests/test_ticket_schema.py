"""Verify the frozen migration against model metadata and existing registry."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from app.api.v1.router import api_router  # loads registry models
from app.db.base_class import Base
from app.db.models.ticket import Ticket, TicketNumberSequence


def test_ticket_migration_round_trip():
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/cap01_ticket.py'
    spec = importlib.util.spec_from_file_location('cap01_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=[t for t in Base.metadata.sorted_tables
                                                     if t.name not in {'ticket', 'ticket_number_sequence'}])
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = inspect(connection)
        assert {c['name'] for c in inspector.get_columns('ticket')} == set(Ticket.__table__.columns.keys())
        assert {i['name'] for i in inspector.get_indexes('ticket')} == {i.name for i in Ticket.__table__.indexes}
        assert len(inspector.get_foreign_keys('ticket')) == 17
        migration.downgrade()
        assert 'ticket' not in inspect(connection).get_table_names()
        assert 'organization' in inspect(connection).get_table_names()
    engine.dispose()
