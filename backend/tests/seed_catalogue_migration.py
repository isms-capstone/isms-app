"""Fixture for a populated dual-catalogue migration; only disposable CI databases."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sqlalchemy as sa


def seed(bind):
    metadata = sa.MetaData()
    def table(name):
        return sa.Table(name, metadata, autoload_with=bind)
    now = datetime(2026, 10, 5)
    bind.execute(table('teams').insert(), {'id': 50, 'name': 'Migration QA Team'})
    bind.execute(table('organization').insert(), {'id': 50, 'name': 'Migration QA Org', 'is_active': True})
    bind.execute(table('product').insert(), [
        {'id': 1, 'code': 'legacy-exam', 'name': 'Migration Exam', 'is_active': True, 'default_team_id': 50},
        {'id': 2, 'code': 'legacy-logbook', 'name': 'Migration Logbook', 'is_active': True, 'default_team_id': None}])
    bind.execute(table('products').insert(), {'id': 10, 'name': 'Migration Exam', 'is_active': True, 'created_at': now, 'updated_at': now})
    bind.execute(table('modules').insert(), {'id': 10, 'product_id': 10, 'name': 'Teacher', 'is_active': True, 'created_at': now, 'updated_at': now})
    bind.execute(table('product_module').insert(), {'id': 1, 'product_id': 1, 'code': 'legacy-teacher', 'name': 'Teacher', 'is_active': True})
    bind.execute(table('product_instance').insert(), {'id': 50, 'organization_id': 50, 'product_id': 1, 'code': 'production', 'name': 'Migrated customer installation', 'version': '1.0', 'environment': 'production', 'url': 'https://example.org', 'is_active': True})


def verify(bind):
    metadata = sa.MetaData()
    def table(name):
        return sa.Table(name, metadata, autoload_with=bind)
    products = table('products')
    product = bind.execute(sa.select(products).where(products.c.name == 'Migration Exam')).mappings().one()
    assert product['id'] == 10 and product['code'] == 'legacy-exam' and product['default_team_id'] == 50
    instances = table('product_instance')
    assert bind.execute(sa.select(instances.c.product_id).where(instances.c.id == 50)).scalar_one() == 10
    modules = table('modules')
    module = bind.execute(sa.select(modules).where(modules.c.id == 10)).mappings().one()
    assert module['code'] == 'legacy-teacher' and module['product_id'] == 10
    assert bind.execute(sa.select(sa.func.count()).select_from(products).where(products.c.name == 'Migration Logbook')).scalar_one() == 1
    # Reproduce an older ADM writer that does not know about registry code columns.
    bind.execute(sa.text('INSERT INTO products (name, is_active, created_at, updated_at) '
                        'VALUES (:name, 1, :stamp, :stamp)'),
                 {'name': 'Old ADM Writer QA', 'stamp': '2026-10-05 00:00:00'})
    added = bind.execute(sa.select(products).where(products.c.name == 'Old ADM Writer QA')).mappings().one()
    assert added['code'] and len(added['code']) <= 50
    bind.execute(sa.text('INSERT INTO modules (product_id, name, is_active, created_at, updated_at) '
                        'VALUES (:product, :name, 1, :stamp, :stamp)'),
                 {'product': added['id'], 'name': 'Old ADM Module QA', 'stamp': '2026-10-05 00:00:00'})
    added_module = bind.execute(sa.select(modules).where(modules.c.product_id == added['id'])).mappings().one()
    assert added_module['code'] and len(added_module['code']) <= 50


if __name__ == '__main__':
    import os
    from app.core.config import settings
    from app.db.session import engine
    assert os.getenv('REGISTRY_MARIADB_QA') == '1' and settings.MARIADB_DB == 'isms_registry_qa'
    with engine.begin() as connection:
        {'seed': seed, 'verify': verify}[sys.argv[1]](connection)
