"""Cross-module contracts: both UIs/APIs use one ADM catalogue."""
from types import SimpleNamespace

from app.api.deps import get_current_user
from test_registry_auth_ui import authenticated_app


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
