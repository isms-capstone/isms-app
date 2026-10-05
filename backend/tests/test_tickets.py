"""Capture integration, also run on the migrated MariaDB in CI."""
import os
from datetime import datetime, timedelta, timezone
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.router import api_router
from app.db.base_class import Base
from app.db.models.ticket import Ticket, TicketNumberSequence
from app.db.models.user import Role, User
from app.db.session import get_db


@pytest.fixture
def capture():
    external = os.getenv('REGISTRY_MARIADB_QA') == '1'
    if external:
        from app.db.session import engine
    else:
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    key = uuid4().hex[:12]
    with factory() as db:
        role = db.scalar(select(Role).where(Role.name == 'Admin'))
        if not role:
            role = Role(name='Admin'); db.add(role); db.flush()
        user = User(username=key, email=f'{key}@example.org', hashed_password='unused', role_id=role.id)
        db.add(user); db.commit(); user_id = user.id
    app = FastAPI(); app.include_router(api_router, prefix='/api/v1')
    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=SimpleNamespace(name='Admin'))
    with TestClient(app) as client:
        def post(path, body):
            result = client.post('/api/v1' + path, json=body)
            assert result.status_code in (200, 201), result.text
            return result.json()
        org = post('/customers/organizations', {'name': key})['id']
        other = post('/customers/organizations', {'name': key + ' other'})['id']
        contact = post(f'/customers/organizations/{org}/contacts', {'name': 'Teacher'})['id']
        product = post('/products', {'code': key, 'name': key})['id']
        module = post(f'/products/{product}/modules', {'code': 'teacher', 'name': 'Teacher'})['id']
        instance = post(f'/organizations/{org}/products/{product}/instances',
                        {'code': 'prod', 'name': 'Exam', 'version': '1', 'environment': 'production', 'url': 'https://example.org'})['id']
        category = post('/admin/master-data/problem-types', {'module_id': module, 'name': 'Login'})['id']
        yield client, app, factory, {'organization_id': org, 'contact_id': contact,
                                  'product_instance_id': instance, 'module_id': module, 'category_id': category}, other
    if not external:
        engine.dispose()


def test_draft_and_minimal_new(capture):
    client, _, factory, data, _ = capture
    for body in ({}, {'subject': '   '}, {'subject': 'x', 'channel': 'email'}):
        result = client.post('/api/v1/tickets', json=body)
        assert result.status_code == 201, result.text
        assert result.json()['status'] == 'DRAFT'
        assert result.json()['ticket_no'] is None
    start = perf_counter()
    result = client.post('/api/v1/tickets', json={'contact_id': data['contact_id'], 'subject': ' Login ', 'channel': 'email'})
    elapsed = (perf_counter() - start) * 1000
    assert result.status_code == 201, result.text
    record = result.json()
    assert record['status'] == 'NEW' and record['subject'] == 'Login'
    assert record['organization_id'] == data['organization_id']
    assert record['ticket_no'].startswith('DVHT-') and len(record['ticket_no']) == 17
    assert record['created_at'].endswith('Z') and record['reported_at'].endswith('Z')
    assert elapsed < 500, f'Local/CI normal-fixture latency {elapsed:.1f}ms'
    assert client.get(f"/api/v1/tickets/{record['id']}").json() == record
    assert client.delete(f"/api/v1/tickets/{record['id']}").status_code == 405


def test_scoped_references(capture):
    client, _, _, data, other = capture
    body = dict(data, subject='Login', channel='phone')
    assert client.post('/api/v1/tickets', json=body).status_code == 201
    for changes in ({'organization_id': other}, {'contact_id': 999999999}, {'module_id': 999999999},
                    {'product_instance_id': None}, {'status': 'CLOSED'}, {'ticket_no': 'manual'}, {'channel': 'invalid'}):
        result = client.post('/api/v1/tickets', json=body | changes)
        assert result.status_code in (404, 422), result.text
    dept = client.post(f'/api/v1/customers/organizations/{other}/departments', json={'name': 'Other dept'}).json()['id']
    assert client.post('/api/v1/tickets', json=body | {'department_id': dept}).status_code == 422


def test_time_and_exam_snapshot(capture):
    client, _, _, data, _ = capture
    now = datetime.now(timezone.utc)
    window = {'name': 'Current exam', 'starts_at': (now - timedelta(hours=1)).isoformat(),
              'ends_at': (now + timedelta(hours=1)).isoformat()}
    assert client.post(f"/api/v1/customers/organizations/{data['organization_id']}/exam-windows", json=window).status_code == 201
    body = dict(data, subject='Issue', channel='portal')
    assert client.post('/api/v1/tickets', json=body).json()['is_exam_window'] is True
    for reported in ((now - timedelta(days=8)).isoformat(), (now + timedelta(minutes=5)).isoformat(), now.replace(tzinfo=None).isoformat()):
        assert client.post('/api/v1/tickets', json=body | {'reported_at': reported}).status_code == 422


def test_numbering_and_permissions(capture):
    client, app, factory, data, _ = capture
    body = dict(data, subject='Issue', channel='email')
    numbers = [client.post('/api/v1/tickets', json=body).json()['ticket_no'] for _ in range(5)]
    assert len(set(numbers)) == 5
    assert int(numbers[-1][-5:]) - int(numbers[0][-5:]) == 4
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=SimpleNamespace(name='Executive'))
    assert client.post('/api/v1/tickets', json=body).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.get('/api/v1/tickets').status_code == 401
