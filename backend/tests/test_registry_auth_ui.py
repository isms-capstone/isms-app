import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.router import api_router
from app.core.security import get_password_hash
from app.db.base_class import Base
from app.db.models.user import Role, User
from app.db.session import get_db
from app.registry_ui import mount_registry_ui


@pytest.fixture
def authenticated_app(tmp_path):
    engine = create_engine(f'sqlite:///{(tmp_path / "auth-qa.sqlite").as_posix()}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        # Real role IDs deliberately differ from legacy 4/5/6.
        roles = [Role(id=20, name='Admin'), Role(id=21, name='Agent'), Role(id=22, name='Auditor')]
        db.add_all(roles); db.flush()
        hashed = get_password_hash('test-only-password')
        for name, role_id in [('qa-admin', 20), ('qa-agent', 21), ('qa-auditor', 22)]:
            db.add(User(username=name, email=f'{name}@example.org', hashed_password=hashed, role_id=role_id, is_active=True))
        db.commit()
    app = FastAPI(); app.include_router(api_router, prefix='/api/v1'); mount_registry_ui(app)
    def database():
        with factory() as db: yield db
    app.dependency_overrides[get_db] = database
    with TestClient(app) as client: yield client
    engine.dispose()


def test_actual_login_jwt_rbac_and_ui_assets(authenticated_app):
    client = authenticated_app
    page = client.get('/registry')
    assert page.status_code == 200
    assert 'Customers &amp; Products' in page.text or 'Customers & Products' in page.text
    assert "script-src 'self'" in page.headers['content-security-policy']
    assert client.get('/registry/assets/registry.js').status_code == 200
    assert client.get('/registry/assets/autocomplete.js').status_code == 200
    assert client.get('/api/v1/customers/organizations').status_code == 401
    assert client.post('/api/v1/auth/login', data={'username': 'qa-admin', 'password': 'wrong'}).status_code == 401
    tokens = {}
    for name in ['qa-admin', 'qa-agent', 'qa-auditor']:
        response = client.post('/api/v1/auth/login', data={'username': name, 'password': 'test-only-password'})
        assert response.status_code == 200, response.text
        tokens[name] = {'Authorization': f'Bearer {response.json()["access_token"]}'}
    product = client.post('/api/v1/products', headers=tokens['qa-admin'], json={'code': 'exam', 'name': 'Exam'})
    assert product.status_code == 201
    assert client.post('/api/v1/products', headers=tokens['qa-agent'], json={'code': 'denied', 'name': 'Denied'}).status_code == 403
    assert client.post('/api/v1/customers/organizations', headers=tokens['qa-agent'], json={'name': 'TU'}).status_code == 201
    assert client.post('/api/v1/customers/organizations', headers=tokens['qa-auditor'], json={'name': 'Denied'}).status_code == 403
    assert client.get('/api/v1/registry/session', headers=tokens['qa-admin']).json()['can_edit_products'] is True
    assert client.get('/api/v1/customers/autocomplete?q=TU', headers=tokens['qa-agent']).json()[0]['organization']['name'] == 'TU'
    assert client.get('/api/v1/products', headers={'Authorization': 'Bearer malformed'}).status_code == 401
