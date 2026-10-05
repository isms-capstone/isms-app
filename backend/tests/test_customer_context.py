import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.autogenerate import compare_metadata

from app.api.deps import get_current_user
from app.db.models.customer import Organization
from app.db.base_class import Base
from app.db.models.customer_context import Department, ExamWindow
from app.db.models.user import Team
from app.db.models.product import Product, ProductInstance
from app.db.session import get_db
from app.services.product_search import product_preference_order, resolve_search_context
from test_customers import api
from test_products import role, instance_body


def organizations(client):
    return [client.post('/customers/organizations', json={'name': name}).json()['id'] for name in ['TU', 'CU']]


def test_reusable_customer_context_and_scope(api):
    client, _ = api
    one, two = organizations(client)
    path = f'/customers/organizations/{one}'
    department = client.post(f'{path}/departments', json={'name': ' Medicine   Faculty '})
    assert department.status_code == 201
    assert department.json()['name'] == 'Medicine Faculty'
    assert client.post(f'{path}/departments', json={'name': 'medicine faculty'}).status_code == 409
    assert client.post(f'/customers/organizations/{two}/departments', json={'name': 'Medicine Faculty'}).status_code == 201
    assert client.put(f'/customers/organizations/{two}/departments/{department.json()["id"]}', json={'name': 'Wrong'}).status_code == 404
    first = client.post(f'{path}/courses', json={'name': ' MED  101 ', 'kind': 'course'})
    reused = client.post(f'{path}/courses', json={'name': 'med 101', 'kind': 'course'})
    assert first.status_code == 201
    assert reused.status_code == 200
    assert first.json()['id'] == reused.json()['id']
    assert client.post(f'{path}/courses', json={'name': 'MED 101', 'kind': 'exam'}).status_code == 201
    assert len(client.get(f'{path}/courses?kind=exam').json()) == 1
    assert len(client.get(f'{path}/departments?q=medicine').json()) == 1
    assert client.get(f'{path}/departments?q=%25').json() == []
    assert client.get(f'{path}/courses?kind=bad').status_code == 422
    assert client.get('/customers/organizations/999/courses').status_code == 404
    course_id = first.json()['id']
    assert client.put(f'{path}/courses/{course_id}', json={'name': 'MED 101', 'is_active': False}).status_code == 200
    assert client.post(f'{path}/courses', json={'name': 'MED 101'}).status_code == 409
    assert client.get(f'{path}/courses?kind=course&is_active=true').json() == []


def test_contract_patch_validates_merged_dates(api):
    client, _ = api
    org, _ = organizations(client)
    path = f'/customers/organizations/{org}/contract'
    assert client.patch(path, json={'contract_start_date': '2026-10-01', 'contract_end_date': '2027-09-30'}).status_code == 200
    assert client.patch(path, json={'contract_end_date': '2026-09-30'}).status_code == 422
    assert client.get(path).json()['contract_end_date'] == '2027-09-30'
    assert client.patch(path, json={'contract_start_date': '2028-01-01'}).status_code == 422
    assert client.patch(path, json={'contract_end_date': None}).json()['contract_start_date'] == '2026-10-01'
    assert client.patch(path, json={'unknown': 1}).status_code == 422


def window_body(**changes):
    return {'name': 'Final exam', 'starts_at': '2026-10-05T09:00:00+07:00', 'ends_at': '2026-10-05T12:00:00+07:00', **changes}


def test_exam_window_timezone_scope_and_boundaries(api):
    client, _ = api
    one, two = organizations(client)
    path = f'/customers/organizations/{one}'
    department = client.post(f'{path}/departments', json={'name': 'Medicine'}).json()['id']
    other_department = client.post(f'/customers/organizations/{two}/departments', json={'name': 'Other'}).json()['id']
    created = client.post(f'{path}/exam-windows', json=window_body(department_id=department))
    assert created.status_code == 201, created.text
    assert created.json()['starts_at'] == '2026-10-05T02:00:00Z'
    assert client.post(f'{path}/exam-windows', json=window_body(department_id=other_department)).status_code == 404
    assert client.post(f'{path}/exam-windows', json=window_body(starts_at='2026-10-05T09:00:00')).status_code == 422
    assert client.post(f'{path}/exam-windows', json=window_body(ends_at='2026-10-05T09:00:00+07:00')).status_code == 422
    assert client.post(f'{path}/exam-windows', json=window_body(name='Organization-wide')).status_code == 201
    assert len(client.get(f'{path}/exam-windows', params={'department_id': department, 'active_at': '2026-10-05T09:00:00+07:00'}).json()) == 2
    assert client.get(f'{path}/exam-windows', params={'active_at': '2026-10-05T12:00:00+07:00'}).json() == []
    assert client.get(f'{path}/exam-windows?active_at=2026-10-05T09:00:00').status_code == 422
    assert client.put(f'/customers/organizations/{two}/exam-windows/{created.json()["id"]}', json=window_body()).status_code == 404
    assert client.put(f'{path}/exam-windows/{created.json()["id"]}', json=window_body(is_active=False)).status_code == 200
    assert len(client.get(f'{path}/exam-windows', params={'active_at': '2026-10-05T10:00:00+07:00'}).json()) == 1


def test_autocomplete_selection_only_active_organization_data(api):
    client, app = api
    one, two = organizations(client)
    contact = client.post(f'/customers/organizations/{one}/contacts', json={'name': 'Somchai'}).json()['id']
    client.post(f'/customers/contacts/{contact}/channels', json={'channel_type': 'line_user_id', 'value': 'U123'})
    assert client.get('/customers/autocomplete?q=U123').json()[0]['contact']['id'] == contact
    assert client.get('/customers/autocomplete?q=TU').json()[0]['organization']['id'] == one
    assert client.get('/customers/autocomplete?q=%25').json() == []
    assert client.get('/customers/autocomplete?q= ').json() == []
    assert client.get('/customers/autocomplete?limit=21&q=TU').status_code == 422
    role(app, 'Admin')
    product = client.post('/products', json={'code': 'exam', 'name': 'Exam'}).json()['id']
    instance = client.post(f'/organizations/{one}/products/{product}/instances', json=instance_body()).json()['id']
    client.post(f'/organizations/{two}/products/{product}/instances', json=instance_body())
    client.post(f'/customers/organizations/{one}/departments', json={'name': 'Medicine'})
    client.post(f'/customers/organizations/{one}/courses', json={'name': 'MED101'})
    context_path = f'/customers/organizations/{one}/selection-context'
    context = client.get(context_path, params={'contact_id': contact})
    assert context.status_code == 200
    assert [row['id'] for row in context.json()['instances']] == [instance]
    assert len(context.json()['departments']) == 1
    assert len(context.json()['courses']) == 1
    assert client.get(f'/customers/organizations/{two}/selection-context?contact_id={contact}').status_code == 404
    client.put(f'/products/{product}', json={'code': 'exam', 'name': 'Exam', 'is_active': False})
    assert client.get(context_path).json()['instances'] == []
    client.put(f'/customers/organizations/{one}', json={'name': 'TU', 'is_active': False})
    assert client.get('/customers/autocomplete?q=Somchai').json() == []
    assert client.get(context_path).status_code == 409


def test_default_team_and_same_product_ranking_hook(api):
    client, app = api
    role(app, 'Admin')
    one, two = organizations(client)
    products = [client.post('/products', json={'code': code, 'name': code}).json()['id'] for code in ['exam', 'geta']]
    instances = []
    for org, product in [(one, products[0]), (two, products[0]), (one, products[1])]:
        instances.append(client.post(f'/organizations/{org}/products/{product}/instances', json=instance_body()).json()['id'])
    dependency = app.dependency_overrides[get_db]()
    db = next(dependency)
    try:
        team = Team(name='Support'); db.add(team); db.commit(); db.refresh(team)
        assert client.put(f'/products/{products[0]}/default-team', json={'default_team_id': team.id}).status_code == 200
        assert client.get(f'/products/{products[0]}/routing-context').json()['default_team_id'] == team.id
        assert client.put(f'/products/{products[0]}/default-team', json={'default_team_id': 999}).status_code == 404
        assert client.get('/registry/teams').json()[0]['name'] == 'Support'
        context = resolve_search_context(db, instances[0])
        ids = db.scalars(select(ProductInstance.id).order_by(product_preference_order(ProductInstance.product_id, context), ProductInstance.id.desc())).all()
        assert ids == [instances[1], instances[0], instances[2]]
        assert client.get('/registry/search-context', params={'product_instance_id': instances[0]}).json()['preferred_product_id'] == products[0]
        assert client.get('/registry/search-context').json()['preferred_product_id'] is None
        assert client.get('/registry/search-context?product_instance_id=999').status_code == 404
        role(app, 'Agent')
        assert client.put(f'/products/{products[0]}/default-team', json={'default_team_id': None}).status_code == 403
        role(app, 'Admin')
        assert client.put(f'/products/{products[0]}/default-team', json={'default_team_id': None}).json()['default_team_id'] is None
    finally:
        dependency.close()


def test_new_registry_writes_are_read_only_for_auditor(api):
    client, app = api
    org, _ = organizations(client)
    role(app, 'Auditor')
    for resource, body in [('departments', {'name': 'Denied'}), ('courses', {'name': 'Denied'}), ('exam-windows', window_body())]:
        assert client.post(f'/customers/organizations/{org}/{resource}', json=body).status_code == 403
    assert client.patch(f'/customers/organizations/{org}/contract', json={}).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.get('/customers/autocomplete?q=TU').status_code == 401


def test_complete_migration_chain_and_database_scope_constraints():
    engine = create_engine('sqlite://')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    directory = Path(__file__).resolve().parents[1] / 'alembic/versions'
    files = ['320181f14c87_initial_schema_roles_teams_users.py', 'fef2a1063bc1_initial_isms_schema.py',
             'cusprd01_customer_registry.py', 'cusprd02_product_registry.py', 'cusprd05_customer_context.py',
             'cusprd03_contract_calendar.py', 'cusprd08_product_team.py',
             '8d2c4a1b7e90_add_adm02_master_data_phase1.py',
             'c4e7f1a9b2d3_add_adm04_sla_and_business_calendar.py', 'cusadm01_shared_catalogue.py', 'cusprd07_product_sla.py']
    modules = []
    with engine.begin() as connection:
        for filename in files:
            spec = importlib.util.spec_from_file_location(filename[:-3], directory / filename)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.op = Operations(MigrationContext.configure(connection)); module.upgrade(); modules.append(module)
        assert 'default_team_id' in {c['name'] for c in inspect(connection).get_columns('products')}
        registry_tables = {'organization', 'contact', 'channel_identity', 'products',
                           'modules', 'product_instance', 'department', 'course_or_exam', 'exam_window'}
        context = MigrationContext.configure(connection, opts={
            'include_object': lambda obj, name, type_, reflected, compare_to:
                type_ != 'table' or name in registry_tables,
        })
        assert compare_metadata(context, Base.metadata) == [], 'Registry ORM and migrated schema differ'
    with Session(engine) as db:
        one = Organization(name='TU', is_active=True); two = Organization(name='CU', is_active=True)
        db.add_all([one, two]); db.commit()
        department = Department(organization_id=two.id, name='Other', name_key='other', is_active=True)
        db.add(department); db.commit()
        db.add(ExamWindow(organization_id=one.id, department_id=department.id, name='Wrong', starts_at=datetime(2026, 10, 1), ends_at=datetime(2026, 10, 2), is_active=True))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        one.contract_start_date = datetime(2026, 10, 2).date(); one.contract_end_date = datetime(2026, 10, 1).date()
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
    # Clear test rows before testing schema rollback with SQLite FK enforcement.
    with engine.begin() as connection:
        connection.execute(Department.__table__.delete()); connection.execute(Organization.__table__.delete())
        for module in reversed(modules):
            module.op = Operations(MigrationContext.configure(connection))
            module.downgrade()
        assert inspect(connection).get_table_names() == []
    engine.dispose()
