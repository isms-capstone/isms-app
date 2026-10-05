"""Cross-module contracts: both UIs/APIs use one ADM catalogue."""
from types import SimpleNamespace

from app.api.deps import get_current_user
from test_registry_auth_ui import authenticated_app


def test_merged_adm_cap_migration_graph_roundtrip():
    import importlib.util
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, event, inspect

    directory = Path(__file__).resolve().parents[1] / 'alembic'
    config = Config()
    config.set_main_option('script_location', str(directory))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ['cusadm02']
    engine = create_engine('sqlite://')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    modules = []
    with engine.begin() as connection:
        for revision in reversed(list(script.walk_revisions())):
            spec = importlib.util.spec_from_file_location(revision.revision, revision.path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            modules.append(module)
        assert {'ticket', 'organization', 'products', 'case_templates', 'canned_messages',
                'automation_rules'} <= set(inspect(connection).get_table_names())
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        for module in reversed(modules):
            module.op = Operations(MigrationContext.configure(connection))
            module.downgrade()
        assert inspect(connection).get_table_names() == []
    engine.dispose()


def test_adm_templates_rules_share_catalogue_and_enforce_auth(authenticated_app):
    client = authenticated_app
    def auth(name):
        response = client.post('/api/v1/auth/login', data={'username': name, 'password': 'test-only-password'})
        return {'Authorization': 'Bearer ' + response.json()['access_token']}
    admin, agent = auth('qa-admin'), auth('qa-agent')
    product = client.post('/api/v1/products', headers=admin,
                          json={'code': 'shared', 'name': 'Shared'}).json()['id']
    module = client.post(f'/api/v1/products/{product}/modules', headers=admin,
                         json={'code': 'teacher', 'name': 'Teacher'}).json()['id']
    prefix = '/api/v1/admin/master-data'
    problem = client.post(prefix + '/problem-types', headers=admin,
                          json={'module_id': module, 'name': 'Login'}).json()['id']
    body = {'name': 'Shared template', 'product_id': product, 'module_id': module,
            'problem_type_id': problem, 'default_severity': 'S2'}
    assert client.post(prefix + '/case-templates', headers=agent, json=body).status_code == 403
    response = client.post(prefix + '/case-templates', headers=admin, json=body)
    assert response.status_code == 201, response.text
    assert client.get('/api/v1/master-data/case-templates', headers=agent).json()[0]['product_id'] == product
    team = client.post('/api/v1/teams/', headers=admin, json={'name': 'Routing Team'}).json()['id']
    rules = '/api/v1/admin/automation-rules'
    body = {'name': 'Product routing', 'condition_field': 'product_id', 'condition_value': str(product),
            'action_team_id': team}
    assert client.post(rules, headers=agent, json=body).status_code == 403
    response = client.post(rules, headers=admin, json=body)
    assert response.status_code == 201, response.text
    rule_id = response.json()['id']
    assert client.patch(f'{rules}/{rule_id}', headers=admin, json={'priority': 2}).json()['priority'] == 2
    assert client.delete(f'{rules}/{rule_id}', headers=admin).json()['is_active'] is False
    assert client.get(rules + '?active=true', headers=admin).json() == []
    assert client.get(rules).status_code == 401


def test_adm_catalogue_is_shared_with_registry(authenticated_app):
    client = authenticated_app
    login = client.post('/api/v1/auth/login', data={'username': 'qa-admin', 'password': 'test-only-password'})
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    path = '/api/v1/admin/master-data'
    product = client.post(path + '/products', headers=headers, json={'name': 'Shared Exam'}).json()
    product_id = product['id']
    registry = client.get(f'/api/v1/products/{product_id}', headers=headers)
    assert registry.status_code == 200
    assert registry.json()['name'] == 'Shared Exam'
    assert registry.json()['code'].startswith('adm-')
    module = client.post(path + '/modules', headers=headers, json={'product_id': product_id, 'name': 'Teacher'})
    assert module.status_code == 201, module.text
    assert client.get(f'/api/v1/products/{product_id}/modules', headers=headers).json()[0]['id'] == module.json()['id']
    created = client.post('/api/v1/products', headers=headers, json={'name': 'Registry Product', 'code': 'registry-product'})
    assert created.status_code == 201
    assert created.json()['id'] in [row['id'] for row in client.get(path + '/products', headers=headers).json()]
    assert client.patch(path + f'/products/{product_id}', headers=headers, json={'name': 'Renamed'}).status_code == 200
    assert client.get(f'/api/v1/products/{product_id}', headers=headers).json()['name'] == 'Renamed'
    assert client.delete(path + f'/products/{product_id}', headers=headers).status_code == 200
    assert client.get(f'/api/v1/products/{product_id}', headers=headers).json()['is_active'] is False
    assert client.post('/api/v1/products', headers=headers, json={'name': 'x' * 151, 'code': 'too-long'}).status_code == 422


def test_legacy_user_cannot_write_after_adm_role_alignment(authenticated_app):
    client = authenticated_app
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(username='legacy-user', role=SimpleNamespace(name='User'))
    assert client.post('/api/v1/customers/organizations', json={'name': 'Denied'}).status_code == 403
    assert client.get('/api/v1/registry/session').json()['can_edit_customers'] is False
