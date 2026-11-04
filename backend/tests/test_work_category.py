"""WRK-01/02 and CAT-01..07 acceptance, with the real CAP/CORE routers."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from app.api.deps import get_current_user
from app.db.models.ticket import Ticket
from app.db.models.work_category import (
    CategoryUsage,
    TicketAudit,
    TicketTag,
    TicketWorklog,
)
from sqlalchemy import func, select
from test_tickets import capture


def create(client, context, **extra):
    response = client.post('/api/v1/tickets', json=context | {'subject': 'WRK CAT QA', 'channel': 'phone'} | extra)
    assert response.status_code == 201, response.text
    return response.json()


def post(client, path, body):
    response = client.post('/api/v1' + path, json=body)
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_category_edit_preserves_legacy_intake_channel(capture):
    client, _, factory, context, _ = capture
    ticket = create(client, context)
    with factory() as db:
        db.get(Ticket, ticket['id']).channel = 'WEB'
        db.commit()
    response = client.patch(f"/api/v1/tickets/{ticket['id']}/categorization", json={'tags': ['legacy-channel-qa']})
    assert response.status_code == 200, response.text
    assert response.json()['channel'] == 'WEB'
    assert response.json()['status'] == ticket['status']
    from app.db.models.master_data import TicketType
    with factory() as db:
        for name in ['Request', 'Bugs', 'Issues']:
            if not db.scalar(select(TicketType).where(TicketType.name == name)):
                db.add(TicketType(name=name))
        db.commit()
    options = client.get('/api/v1/categorization/options').json()
    assert [row['name'] for row in options['ticket_types']][:3] == ['Issues', 'Bugs', 'Request']


@pytest.mark.parametrize('impact,exam,expected', [
    ('organization', True, 'S1'), ('organization', False, 'S2'),
    ('group', True, 'S2'), ('group', False, 'S3'),
    ('single_user', True, 'S3'), ('single_user', False, 'S3'),
    ('non_disruptive', True, 'S3'), ('non_disruptive', False, 'S4')])
def test_srs_13_1_and_capture_persistence(capture, impact, exam, expected):
    client, _, _, context, _ = capture
    suggestion = client.get('/api/v1/categorization/severity-suggestion', params={'impact_scope': impact, 'is_exam_window': exam})
    assert suggestion.status_code == 200, suggestion.text
    assert suggestion.json()['severity'] == expected
    ticket = create(client, context, impact_scope=impact, is_exam_window=exam)
    assert ticket['severity'] == expected and ticket['impact_scope'] == impact
    assert ticket['is_exam_window'] is exam


def test_worklog_identity_channel_timeline_and_validation(capture):
    client, _, factory, context, _ = capture
    ticket = create(client, context)
    path = f"/tickets/{ticket['id']}/worklogs"
    note = post(client, path, {'kind': 'internal_note', 'body': ' ข้อมูลภายใน '})
    reply = post(client, path, {'kind': 'public_reply', 'body': 'แจ้งลูกค้าแล้ว', 'channel': 'line_oa'})
    assert note['body'] == 'ข้อมูลภายใน' and note['channel'] is None
    assert reply['channel'] == 'line_oa' and reply['actor_id'] == ticket['created_by_id']
    assert reply['created_at'].endswith('+00:00')
    assert client.get('/api/v1' + path).json() == [note, reply]
    events = client.get(f"/api/v1/tickets/{ticket['id']}/timeline").json()['items']
    assert [item['kind'] for item in events if item['kind'] in ('internal_note', 'public_reply')] == ['internal_note', 'public_reply']
    assert [event['created_at'] for event in events] == sorted(event['created_at'] for event in events)
    assert next(event for event in events if event['kind'] == 'public_reply')['channel'] == 'line_oa'
    # Case intake channel must not be mistaken for the reply delivery channel.
    assert client.get(f"/api/v1/tickets/{ticket['id']}").json()['channel'] == 'phone'
    for body in ({'kind': 'public_reply', 'body': 'missing channel'},
                 {'kind': 'internal_note', 'body': 'leak', 'channel': 'email'},
                 {'kind': 'internal_note', 'body': '  '},
                 {'kind': 'internal_note', 'body': 'x' * 20001},
                 {'kind': 'private', 'body': 'invalid'},
                 {'kind': 'internal_note', 'body': 'x', 'actor_id': 999}):
        assert client.post('/api/v1' + path, json=body).status_code == 422
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(TicketWorklog).where(TicketWorklog.ticket_id == ticket['id'])) == 2
        audits = db.scalars(select(TicketAudit).where(TicketAudit.event == 'worklog_created', TicketAudit.ticket_id == ticket['id'])).all()
        assert len(audits) == 2
        assert all(row.actor_id == ticket['created_by_id'] for row in audits)
    assert client.get('/api/v1/tickets/99999999/timeline').status_code == 404


def test_staff_permissions_and_no_customer_access(capture):
    client, app, factory, context, _ = capture
    ticket = create(client, context)
    for role in ('Customer', 'Executive', 'Auditor'):
        app.dependency_overrides[get_current_user] = lambda role=role: SimpleNamespace(id=ticket['created_by_id'], role=SimpleNamespace(name=role))
        for suffix in ('worklogs', 'timeline', 'audit', 'categorization'):
            assert client.get(f"/api/v1/tickets/{ticket['id']}/{suffix}").status_code == 403
        assert client.post(f"/api/v1/tickets/{ticket['id']}/worklogs", json={'kind': 'internal_note', 'body': 'no'}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=ticket['created_by_id'] + 500, role=SimpleNamespace(name='Agent'))
    assert client.patch(f"/api/v1/tickets/{ticket['id']}/categorization", json={'tags': ['no']}).status_code == 403
    assert client.post(f"/api/v1/tickets/{ticket['id']}/worklogs", json={'kind': 'internal_note', 'body': 'no'}).status_code == 403
    assert client.get('/api/v1/categorization/popular-tags').status_code == 403
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(TicketWorklog).where(TicketWorklog.ticket_id == ticket['id'])) == 0


def test_override_codes_tags_audit_and_no_lifecycle_changes(capture):
    client, _, factory, context, _ = capture
    ticket = create(client, context, impact_scope='organization', is_exam_window=True)
    path = f"/api/v1/tickets/{ticket['id']}/categorization"
    assert client.patch(path, json={'severity': 'S4', 'severity_overridden_reason': ' '}).status_code == 422
    assert client.patch(path, json={'severity': 'S4', 'severity_overridden_reason': 'ระบบสำรองรองรับได้'}).status_code == 200
    cause = post(client, '/admin/master-data/cause-codes', {'code': f"QA-{ticket['id']}", 'name': 'Configuration'})['id']
    solution = post(client, '/admin/master-data/solution-codes', {'code': f"QA-{ticket['id']}", 'name': 'Reconfigure'})['id']
    tag = f"exam-{ticket['id']}"
    result = client.patch(path, json={'root_cause_code_id': cause, 'root_cause_detail': ' สาเหตุ ',
        'resolution_code_id': solution, 'resolution_detail': ' แก้ไข ', 'tags': [f' {tag.upper()} ', tag, 'ภาษาไทย']})
    assert result.status_code == 200, result.text
    saved = result.json()
    for key in ('status', 'ticket_no', 'reported_at', 'created_at', 'owner_id', 'assignee_id', 'sla_policy_id'):
        assert saved[key] == ticket[key]
    assert saved['root_cause_detail'] == 'สาเหตุ' and saved['resolution_detail'] == 'แก้ไข'
    assert client.get(path).json()['tags'] == [tag, 'ภาษาไทย']
    report = {row['name']: row['ticket_count'] for row in client.get('/api/v1/categorization/popular-tags').json()}
    assert report[tag] == 1
    before_count = len(client.get(f"/api/v1/tickets/{ticket['id']}/audit").json())
    assert client.patch(path, json={'tags': [tag, 'ภาษาไทย']}).status_code == 200
    assert len(client.get(f"/api/v1/tickets/{ticket['id']}/audit").json()) == before_count
    assert client.patch(path, json={'tags': []}).status_code == 200
    assert tag not in {row['name'] for row in client.get('/api/v1/categorization/popular-tags').json()}
    for bad in ({'tags': ['']}, {'tags': ['a' * 65]}, {'tags': ['x\x00y']}, {'tags': ['x'] * 21},
                {'module_id': 99999999}, {'root_cause_code_id': 99999999}, {'status': 'CLOSED'}):
        assert client.patch(path, json=bad).status_code == 422
    with factory() as db:
        audits = db.scalars(select(TicketAudit).where(TicketAudit.event == 'categorization_updated', TicketAudit.ticket_id == ticket['id'])).all()
        assert any(row.changes.get('severity', {}).get('new') == 'S4' for row in audits)
        assert db.scalar(select(func.count()).select_from(TicketTag).where(TicketTag.ticket_id == ticket['id'])) == 0


def test_product_cascade_independent_axes_and_personal_frequency(capture):
    client, app, factory, context, other = capture
    with factory() as db:
        from app.db.models.product import ProductInstance
        product_id = db.get(ProductInstance, context['product_instance_id']).product_id
    symptom = post(client, '/admin/master-data/symptoms', {'product_id': product_id, 'name': 'Download'})['id']
    stage = post(client, '/admin/master-data/service-stages', {'product_id': product_id, 'name': 'During exam'})['id']
    second = post(client, f'/products/{product_id}/modules', {'code': 'z', 'name': 'Z frequently used'})['id']
    for _ in range(3):
        create(client, {**context, 'module_id': second, 'category_id': None}, symptom_id=symptom, service_stage_id=stage)
    ticket = create(client, context)
    path = f"/api/v1/tickets/{ticket['id']}/categorization"
    preferred = client.get(f'/api/v1/products/{product_id}/categorization-options').json()
    assert preferred['modules'][0]['id'] == second
    # Another user's history must never change this user's dropdown order.
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=ticket['created_by_id'] + 99, role=SimpleNamespace(name='Agent'))
    assert client.get(f'/api/v1/products/{product_id}/categorization-options').json()['modules'][0]['id'] == context['module_id']
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=ticket['created_by_id'], role=SimpleNamespace(name='Admin'))
    updated = client.patch(path, json={'module_id': second, 'symptom_id': symptom, 'service_stage_id': stage})
    assert updated.status_code == 200, updated.text
    assert updated.json()['category_id'] is None and updated.json()['symptom_id'] == symptom
    # Selecting a module must not erase either independent axis.
    assert client.patch(path, json={'module_id': context['module_id']}).json()['service_stage_id'] == stage
    product2 = post(client, '/products', {'code': f"other-{ticket['id']}", 'name': f"Other {ticket['id']}"})['id']
    instance2 = post(client, f"/organizations/{context['organization_id']}/products/{product2}/instances",
        {'code': 'prod2', 'name': 'Other', 'version': '1', 'environment': 'production', 'url': 'https://example.org'})['id']
    invalid = client.patch(path, json={'product_instance_id': instance2, 'symptom_id': symptom})
    assert invalid.status_code == 422
    assert client.get(path).json()['product_instance_id'] == context['product_instance_id']
    changed = client.patch(path, json={'product_instance_id': instance2})
    assert changed.status_code == 200, changed.text
    assert all(changed.json()[key] is None for key in ('module_id', 'category_id', 'symptom_id', 'service_stage_id'))


def test_request_fulfilment_uses_shared_core_guards(capture):
    client, _, factory, context, _ = capture
    types = client.get('/api/v1/categorization/options').json()['ticket_types']
    request_type = next((row['id'] for row in types if row['name'] == 'Request'), None)
    if request_type is None:
        request_type = post(client, '/admin/master-data/ticket-types', {'name': 'Request'})['id']
    cause = post(client, '/admin/master-data/cause-codes', {'code': 'REQ', 'name': 'Service request'})['id']
    solution = post(client, '/admin/master-data/solution-codes', {'code': 'REQ', 'name': 'Delivered'})['id']
    ticket = create(client, context, ticket_type_id=request_type)
    path = f"/tickets/{ticket['id']}/request-workflow"
    assert client.get(f"/api/v1/tickets/{ticket['id']}/categorization").json()['workflow'] == 'request'
    started = post(client, path, {'action': 'start', 'assignee_id': ticket['created_by_id']})
    assert started['status'] == 'IN_PROGRESS'
    assert client.post('/api/v1' + path, json={'action': 'fulfil', 'fulfilment_detail': 'Done'}).status_code == 422
    updated = client.patch(f"/api/v1/tickets/{ticket['id']}/categorization", json={'root_cause_code_id': cause, 'resolution_code_id': solution})
    assert updated.status_code == 200, updated.text
    assert post(client, path, {'action': 'fulfil', 'fulfilment_detail': ' ส่งออกข้อมูลเรียบร้อย '})['status'] == 'RESOLVED'
    assert post(client, path, {'action': 'confirm'})['status'] == 'CLOSED'
    # Metadata correction on a closed case does not reopen it or reset its SLA.
    assert client.patch(f"/api/v1/tickets/{ticket['id']}/categorization", json={'tags': ['completed']}).json()['status'] == 'CLOSED'
    incident = create(client, context)
    assert client.post(f"/api/v1/tickets/{incident['id']}/request-workflow", json={'action': 'start'}).status_code == 409


def test_calendar_suggestion_and_backwards_compatible_drafts(capture):
    client, _, _, context, _ = capture
    now = datetime.now(timezone.utc)
    post(client, f"/customers/organizations/{context['organization_id']}/exam-windows", {
        'name': 'Exam', 'starts_at': (now - timedelta(hours=1)).isoformat(), 'ends_at': (now + timedelta(hours=1)).isoformat()})
    suggestion = client.get('/api/v1/categorization/severity-suggestion', params={'impact_scope': 'organization', 'organization_id': context['organization_id']}).json()
    assert suggestion['severity'] == 'S1' and suggestion['is_exam_window'] is True
    ticket = create(client, context, impact_scope='organization', tags=['draft'], save_as_draft=True)
    assert ticket['severity'] == 'S1'
    result = client.patch(f"/api/v1/tickets/{ticket['id']}/draft-field", json={'field': 'subject', 'value': 'Edit'})
    assert result.status_code == 200, result.text
    assert result.json()['severity'] == 'S1'
    assert client.get(f"/api/v1/tickets/{ticket['id']}/categorization").json()['tags'] == ['draft']


def test_legacy_assessment_and_core_category_audit(capture):
    client, _, factory, context, _ = capture
    ticket = create(client, context, save_as_draft=True)
    # Published schemas already had severity; imported cases may lack impact scope.
    with factory() as db:
        db.get(Ticket, ticket['id']).severity = 'S2'
        db.commit()
    edited = client.patch(f"/api/v1/tickets/{ticket['id']}/draft-field", json={'field': 'subject', 'value': 'Legacy preserved'})
    assert edited.status_code == 200, edited.text
    assert edited.json()['severity'] == 'S2'
    tags = client.patch(f"/api/v1/tickets/{ticket['id']}/categorization", json={'tags': ['legacy']})
    assert tags.status_code == 200, tags.text
    assert tags.json()['severity'] == 'S2'
    active = create(client, context)
    with factory() as db:
        from app.db.models.master_data import ProblemType
        category = ProblemType(module_id=context['module_id'], name='Other valid category')
        db.add(category)
        db.commit()
        category_id = category.id
    result = client.patch(f"/api/v1/tickets/{active['id']}/status", json={
        'status': 'IN_PROGRESS', 'assignee_id': active['created_by_id'], 'category_id': category_id})
    assert result.status_code == 200, result.text
    audit = client.get(f"/api/v1/tickets/{active['id']}/audit").json()
    assert any(row['changes'].get('category_id') == {'old': context['category_id'], 'new': category_id} for row in audit)


def test_existing_worklog_contract_and_storage_are_preserved(capture):
    client, _, factory, context, _ = capture
    ticket = create(client, context)
    path = f"/tickets/{ticket['id']}/worklogs"
    note = post(client, path, {'message': 'Legacy internal note', 'is_internal': True})
    reply = post(client, path, {'message': 'Legacy LINE OA reply', 'is_internal': False, 'channel': 'line_oa'})
    assert note['body'] == note['message'] == 'Legacy internal note'
    assert note['kind'] == 'internal_note' and note['is_internal'] is True
    assert reply['channel'] == 'line_oa' and reply['is_internal'] is False
    assert client.post('/api/v1' + path, json={'message': 'No actual channel', 'is_internal': False}).status_code == 422
    assert client.post('/api/v1' + path, json={'message': 'Ambiguous', 'body': 'other', 'kind': 'internal_note'}).status_code == 422
    with factory() as db:
        stored = db.get(TicketWorklog, note['id'])
        assert stored.__tablename__ == 'ticket_worklogs'
        assert stored.message == note['body'] and stored.author_id == note['actor_id']
