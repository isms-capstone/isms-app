import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from seed_catalogue_migration import seed, verify


def test_populated_catalogue_merge_preserves_references_and_rollback():
    engine = create_engine('sqlite://')
    directory = Path(__file__).resolve().parents[1] / 'alembic/versions'
    files = ['320181f14c87_initial_schema_roles_teams_users.py', 'fef2a1063bc1_initial_isms_schema.py',
             'cusprd01_customer_registry.py', 'cusprd02_product_registry.py', 'cusprd05_customer_context.py',
             'cusprd03_contract_calendar.py', 'cusprd08_product_team.py',
             '8d2c4a1b7e90_add_adm02_master_data_phase1.py',
             'c4e7f1a9b2d3_add_adm04_sla_and_business_calendar.py', 'cusadm01_shared_catalogue.py']
    with engine.begin() as connection:
        for filename in files:
            spec = importlib.util.spec_from_file_location(filename[:-3], directory / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.op = Operations(MigrationContext.configure(connection))
            if filename == 'cusadm01_shared_catalogue.py':
                seed(connection)
            module.upgrade()
        verify(connection)
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []
        module.downgrade()
        assert connection.execute(text('SELECT product_id FROM product_instance WHERE id=50')).scalar_one() == 1
        assert 'code' not in {row['name'] for row in inspect(connection).get_columns('products')}
    engine.dispose()
