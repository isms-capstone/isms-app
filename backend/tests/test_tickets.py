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


def test_manual_inline_draft_fields_and_permissions(capture):
    client, app, factory, data, other = capture
    original = client.post('/api/v1/tickets', json=dict(data, subject='Draft', channel='phone', save_as_draft=True)).json()
    path = f"/api/v1/tickets/{original['id']}/draft-field"
    result = client.patch(path, json={'field': 'subject', 'value': ' Edited '})
    assert result.status_code == 200, result.text
    edited = result.json()
    assert edited['subject'] == 'Edited' and edited['status'] == 'DRAFT' and edited['ticket_no'] is None
    assert edited['created_at'] == original['created_at'] and edited['reported_at'] == original['reported_at']
    for body in ({'field': 'status', 'value': 'NEW'}, {'field': 'subject', 'value': 123},
                 {'field': 'channel', 'value': 'invalid'}, {'field': 'contact_id', 'value': 999999999},
                 {'field': 'subject', 'value': 'x', 'created_at': original['created_at']}):
        assert client.patch(path, json=body).status_code in (404, 422)
    assert client.get(f"/api/v1/tickets/{original['id']}").json()['subject'] == 'Edited'
    result = client.patch(path, json={'field': 'organization_id', 'value': other})
    assert result.status_code == 200, result.text
    assert result.json()['organization_id'] == other
    assert all(result.json()[field] is None for field in ('contact_id', 'product_instance_id', 'module_id', 'category_id'))
    assert client.patch(path, json={'field': 'contact_id', 'value': data['contact_id']}).status_code == 422
    new = client.post('/api/v1/tickets', json={'organization_id': other, 'subject': 'New', 'channel': 'phone'}).json()
    assert client.patch(f"/api/v1/tickets/{new['id']}/draft-field", json={'field': 'subject', 'value': 'Denied'}).status_code == 409
    user_id = original['created_by_id']
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id + 1000000, role=SimpleNamespace(name='Agent'))
    assert client.patch(path, json={'field': 'subject', 'value': 'Other user'}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=SimpleNamespace(name='Auditor'))
    assert client.patch(path, json={'field': 'subject', 'value': 'Read only'}).status_code == 403


def test_old_draft_can_be_enriched_without_rewriting_capture_times(capture):
    client, _, factory, data, _ = capture
    draft = client.post('/api/v1/tickets', json={'subject': 'Old draft'}).json()
    with factory() as db:
        record = db.get(Ticket, draft['id'])
        record.reported_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=20)
        db.commit()
    before = client.get(f"/api/v1/tickets/{draft['id']}").json()
    edited = client.patch(f"/api/v1/tickets/{draft['id']}/draft-field",
                          json={'field': 'description', 'value': 'More details'})
    assert edited.status_code == 200, edited.text
    assert edited.json()['reported_at'] == before['reported_at']
    assert edited.json()['created_at'] == before['created_at']


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


def test_customer_summary_counts_and_pagination(capture):
    client, _, factory, data, other = capture
    ids = []
    for _ in range(7):
        result = client.post('/api/v1/tickets', json=dict(data, subject='Login', channel='email'))
        assert result.status_code == 201
        ids.append(result.json()['id'])
    # Fixture-only status changes: lifecycle transitions are a separate task.
    with factory() as db:
        for record_id, status in zip(ids, ['NEW', 'IN_PROGRESS', 'PENDING_CUSTOMER', 'RESOLVED', 'CLOSED', 'DUPLICATE', 'CANCELLED']):
            db.get(Ticket, record_id).status = status
        db.commit()
    assert client.post('/api/v1/tickets', json={'organization_id': data['organization_id']}).json()['status'] == 'DRAFT'
    assert client.post('/api/v1/tickets', json={'organization_id': other, 'subject': 'Other', 'channel': 'email'}).status_code == 201
    base = f"/api/v1/customers/organizations/{data['organization_id']}"
    assert client.get(base + '/case-summary').json()['open_count'] == 3
    rows = client.get(base + '/problem-history').json()
    assert len(rows) == 1 and rows[0]['frequency'] == 5
    assert rows[0]['category_id'] == data['category_id']
    assert datetime.fromisoformat(rows[0]['last_reported_at']).utcoffset() == timedelta(0)
    client.post('/api/v1/tickets', json={'organization_id': data['organization_id'], 'subject': 'Unclassified', 'channel': 'phone'})
    rows = client.get(base + '/problem-history?limit=1').json()
    assert rows[0]['frequency'] == 5
    assert client.get(base + '/problem-history?offset=1&limit=1').json()[0]['category_id'] is None
    assert len(client.get(f"/api/v1/tickets?organization_id={data['organization_id']}&open_only=true&limit=2").json()) == 2
    assert len(client.get(f"/api/v1/tickets?organization_id={data['organization_id']}&open_only=true&offset=2&limit=2").json()) == 2
    assert client.get(f'/api/v1/customers/organizations/{other}/case-summary').json()['open_count'] == 1
    assert client.get('/api/v1/customers/organizations/999999999/case-summary').status_code == 404


def test_empty_customer_summary(capture):
    client, _, _, data, _ = capture
    base = f"/api/v1/customers/organizations/{data['organization_id']}"
    assert client.get(base + '/case-summary').json()['open_count'] == 0
    assert client.get(base + '/problem-history').json() == []


def test_concurrent_numbering_and_month_boundary(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from app.api.v1.endpoints.tickets import next_ticket_number
    external = os.getenv('REGISTRY_MARIADB_QA') == '1'
    if external:
        from app.db.session import engine
    else:
        engine = create_engine(f'sqlite:///{(tmp_path / "counter.db").as_posix()}', connect_args={'timeout': 20})
        TicketNumberSequence.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        baseline = db.get(TicketNumberSequence, '209810')
        previous = baseline.value if baseline else 0
    def allocate(_):
        with factory() as db:
            # UTC Sep 30 18:00 is October in Thailand.
            number = next_ticket_number(db, datetime(2098, 9, 30, 18))
            db.commit()
            return number
    with ThreadPoolExecutor(max_workers=4) as executor:
        numbers = list(executor.map(allocate, range(20)))
    assert len(set(numbers)) == 20
    assert all(number.startswith('DVHT-209810-') for number in numbers)
    assert sorted(int(n[-5:]) for n in numbers) == list(range(previous + 1, previous + 21))
    with factory() as db:
        assert next_ticket_number(db, datetime(2098, 10, 31, 18)) == 'DVHT-209811-00001'
        db.rollback()
    if not external:
        engine.dispose()


def test_offline_channels_share_case_queries(capture):
    client, _, _, data, _ = capture
    for channel in ('phone', 'face_to_face'):
        result = client.post('/api/v1/tickets', json=dict(data, subject='Offline contact', channel=channel))
        assert result.status_code == 201 and result.json()['channel'] == channel
    base = f"/api/v1/customers/organizations/{data['organization_id']}"
    assert client.get(base + '/case-summary').json()['open_count'] == 2
    assert client.get(base + '/problem-history').json()[0]['frequency'] == 2


def test_product_policy_snapshot_and_isolation(capture):
    from app.db.models.product import ProductInstance
    client, _, factory, data, _ = capture
    with factory() as db:
        product_id = db.get(ProductInstance, data['product_instance_id']).product_id
    policy = client.post('/api/v1/admin/master-data/sla-policies', json={'name': uuid4().hex}).json()['id']
    assert client.put(f'/api/v1/products/{product_id}/sla-policy', json={'sla_policy_id': policy}).status_code == 200
    body = dict(data, subject='Product case', channel='phone')
    record = client.post('/api/v1/tickets', json=body).json()
    assert record['sla_policy_id'] == policy
    foreign_product = client.post('/api/v1/products', json={'code': uuid4().hex, 'name': uuid4().hex}).json()['id']
    symptom = client.post('/api/v1/admin/master-data/symptoms', json={'name': 'Other product symptom', 'product_id': foreign_product}).json()['id']
    assert client.post('/api/v1/tickets', json=body | {'symptom_id': symptom}).status_code == 422
    assert client.patch(f'/api/v1/admin/master-data/sla-policies/{policy}', json={'is_active': False}).status_code == 200
    assert client.post('/api/v1/tickets', json=body).json()['sla_policy_id'] is None
    assert client.get(f"/api/v1/tickets/{record['id']}").json()['sla_policy_id'] == policy


def test_explicit_draft_and_queue_filters(capture):
    client, _, factory, data, _ = capture
    before = client.get('/api/v1/tickets/queue-summary').json()
    marker = uuid4().hex
    body = dict(data, subject=marker, channel='phone')
    draft = client.post('/api/v1/tickets', json=body | {'save_as_draft': True}).json()
    assert draft['status'] == 'DRAFT' and draft['ticket_no'] is None
    new = client.post('/api/v1/tickets', json=body).json()
    # My Work means Assignee = Me, not merely the person who captured the case.
    assert client.get('/api/v1/tickets', params={'mine': True, 'q': marker}).json() == []
    with factory() as db:
        db.get(Ticket, new['id']).assignee_id = new['created_by_id']
        db.commit()
    summary = client.get('/api/v1/tickets/queue-summary').json()
    assert summary['drafts'] == before['drafts'] + 1
    assert summary['mine'] == before['mine'] + 1
    assert summary['today'] == before['today'] + 1
    assert summary['unassigned'] == before['unassigned']
    assert summary['sla_at_risk'] is None
    mine = client.get('/api/v1/tickets', params={'mine': True, 'open_only': True, 'q': marker}).json()
    assert [row['id'] for row in mine] == [new['id']]
    drafts = client.get('/api/v1/tickets?drafts_only=true').json()
    assert [row['id'] for row in drafts] == [draft['id']]
    assert client.get('/api/v1/tickets', params={'q': marker, 'ticket_status': 'NEW'}).json()[0]['id'] == new['id']
    assert client.get('/api/v1/tickets?ticket_status=invalid').status_code == 422
    assert client.get('/api/v1/tickets', params={'q': '%'}).json() == []
