from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace

from openpyxl import load_workbook
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.models.case_search import CaseExportAudit
from app.db.models.product import ProductInstance
from app.db.models.ticket import Ticket
from app.db.models.user import Team, User
from test_tickets import capture


THAI_QUERIES = (
    'เข้าสู่ระบบไม่ได้', 'หน้าจอค้าง', 'ส่งข้อสอบไม่ได้', 'ระบบไม่ตอบสนอง',
    'โหลดรายชื่อไม่ได้', 'ข้อสอบไม่แสดง', 'ดาวน์โหลดรายงานไม่ได้', 'อัปโหลดรูปไม่ได้',
    'เปิดห้องสอบไม่ได้', 'เวลาสอบไม่ถูกต้อง', 'ผลสอบไม่แสดง', 'ยืนยันคำตอบไม่ได้',
    'ค้นหานักศึกษาไม่พบ', 'เชื่อมต่อเครือข่ายไม่ได้', 'รายงานคะแนนไม่ครบ',
    'บันทึกข้อมูลไม่ได้', 'แนบเอกสารไม่ได้', 'เปิดไฟล์ไม่ได้',
    'ส่งอีเมลไม่ได้', 'พิมพ์รายงานไม่ได้',
)


def test_thai_search_sources_filters_and_exports(capture):
    client, app, factory, context, other_org = capture
    response = client.post('/api/v1/tickets', json={
        **context, 'channel': 'phone', 'subject': '=QA ' + ' '.join(THAI_QUERIES[:4]),
        'description': '\n'.join(THAI_QUERIES[4:12]),
        'impact_scope': 'organization', 'is_exam_window': True,
    })
    assert response.status_code == 201, response.text
    case = response.json()
    assert client.post(f"/api/v1/tickets/{case['id']}/worklogs", json={
        'kind': 'internal_note', 'body': '\n'.join(THAI_QUERIES[12:]),
    }).status_code == 201
    prefix = '/api/v1/case-search'
    with factory() as db:
        ticket = db.get(Ticket, case['id'])
        ticket.assignee_id = case['created_by_id']
        product = db.get(ProductInstance, context['product_instance_id']).product_id
        db.commit()

    now = datetime.now(timezone.utc)
    filters = {
        'status': 'NEW', 'organization_id': context['organization_id'], 'product_id': product,
        'assignee_id': case['created_by_id'], 'severity': 'S1',
        'reported_from': (now - timedelta(days=1)).isoformat(),
        'reported_before': (now + timedelta(days=1)).isoformat(),
    }
    for query in THAI_QUERIES:
        result = client.post(prefix + '/query', json={**filters, 'q': query})
        assert result.status_code == 200, result.text
        assert [item['id'] for item in result.json()['items']] == [case['id']], query
    assert client.post(prefix + '/query', json={**filters, 'organization_id': other_org}).json()['total'] == 0
    assert client.get(prefix + '/options').json()['products']
    csv = client.post(prefix + '/export/csv', json=filters)
    assert csv.status_code == 200, csv.text
    assert "'=QA" in csv.content.decode('utf-8-sig')
    xlsx = client.post(prefix + '/export/xlsx', json=filters)
    assert xlsx.status_code == 200, xlsx.text
    workbook = load_workbook(BytesIO(xlsx.content), read_only=True)
    assert workbook.active['B2'].value.startswith("'=QA")
    workbook.close()
    with factory() as db:
        exports = db.scalars(select(CaseExportAudit).where(CaseExportAudit.actor_id == case['created_by_id'])).all()
        assert {row.format for row in exports} == {'csv', 'xlsx'}
        assert all(row.ticket_ids == [case['id']] and row.created_at for row in exports)
        db.get(Ticket, case['id']).subject = 'ทดสอบหัวข้อใหม่'
        db.commit()
    assert client.post(prefix + '/query', json={'q': THAI_QUERIES[0]}).json()['total'] == 0

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=case['created_by_id'] + 500, role=SimpleNamespace(name='Agent'))
    assert client.post(prefix + '/export/csv', json=filters).status_code == 403
    assert client.post(prefix + '/query', json=filters).json()['total'] == 0


def test_saved_views_apply_only_to_the_owner_or_team(capture):
    client, app, factory, _, _ = capture
    actor = app.dependency_overrides[get_current_user]()
    with factory() as db:
        team = Team(name=f'SEA test team {actor.id}')
        db.add(team)
        db.flush()
        actor.team_id = team.id
        db.get(User, actor.id).team_id = team.id
        db.commit()
    app.dependency_overrides[get_current_user] = lambda: actor
    prefix = '/api/v1/case-search'
    for scope in ('team', 'personal'):
        response = client.post(prefix + '/views', json={
            'name': scope, 'scope': scope, 'filters': {'severity': 'S2'},
        })
        assert response.status_code == 201, response.text
    assert {item['scope'] for item in client.get(prefix + '/views').json()} == {'team', 'personal'}
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=actor.id + 500, team_id=actor.team_id, role=SimpleNamespace(name='Agent'))
    assert [item['scope'] for item in client.get(prefix + '/views').json()] == ['team']
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=actor.id + 500, team_id=None, role=SimpleNamespace(name='Agent'))
    assert client.get(prefix + '/views').json() == []
