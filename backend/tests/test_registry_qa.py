from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

from app.core.security import create_access_token
from app.db.models.user import User
from app.db.session import get_db
from test_customers import api
from test_registry_auth_ui import authenticated_app


def test_invalid_channels_and_unknown_customer_fields(api):
    client, _ = api
    organization = client.post('/customers/organizations', json={'name': 'TU'}).json()['id']
    contact = client.post(f'/customers/organizations/{organization}/contacts', json={'name': 'Teacher'}).json()['id']
    assert client.post(f'/customers/contacts/{contact}/channels', json={'channel_type': 'email', 'value': 'not-an-email'}).status_code == 422
    assert client.post('/customers/organizations', json={'name': 'Wrong', 'unexpected_field': True}).status_code == 422
    assert client.post(f'/customers/organizations/{organization}/contacts', json={'name': 'Wrong', 'organization_id': 999}).status_code == 422
    assert client.get(f'/customers/contacts/{contact}').json()['channels'] == []


def test_actual_jwt_expiry_refresh_token_and_inactive_user(authenticated_app):
    client = authenticated_app
    login = client.post('/api/v1/auth/login', data={'username': 'qa-agent', 'password': 'test-only-password'}).json()
    headers = {'Authorization': f'Bearer {login["access_token"]}'}
    assert client.get('/api/v1/registry/session', headers=headers).status_code == 200
    expired = create_access_token('qa-agent', expires_delta=timedelta(minutes=-1))
    assert client.get('/api/v1/registry/session', headers={'Authorization': f'Bearer {expired}'}).status_code == 401
    assert client.get('/api/v1/registry/session', headers={'Authorization': f'Bearer {login["refresh_token"]}'}).status_code == 401
    dependency = client.app.dependency_overrides[get_db]()
    db = next(dependency)
    try:
        user = db.query(User).filter(User.username == 'qa-agent').one()
        user.is_active = False; db.commit()
        assert client.get('/api/v1/registry/session', headers=headers).status_code in (400, 403)
        assert client.post('/api/v1/auth/login', data={'username': 'qa-agent', 'password': 'test-only-password'}).status_code in (400, 403)
    finally:
        dependency.close()


def test_parallel_registry_reads_keep_actual_login_valid(authenticated_app):
    client = authenticated_app
    login = client.post('/api/v1/auth/login', data={'username': 'qa-admin', 'password': 'test-only-password'}).json()
    headers = {'Authorization': f'Bearer {login["access_token"]}'}
    paths = ['/api/v1/registry/session', '/api/v1/products', '/api/v1/registry/teams',
             '/api/v1/customers/organizations'] * 5
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(lambda path: client.get(path, headers=headers).status_code, paths))
    assert statuses == [200] * len(paths)
