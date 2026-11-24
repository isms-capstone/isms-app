"""Server-side queue: filters, SLA ordering, names and paging."""
from datetime import datetime, timedelta

from app.core.sla_calendar import Schedule
from app.db.models.ticket import Ticket
from test_sla_engine import configure_policy
from test_tickets import capture  # noqa: F401


def test_schedule_add_inverts_seconds_across_weekend():
    calendar = Schedule()
    friday_1600_bkk = datetime(2026, 11, 13, 9, 0)  # UTC
    due = calendar.add(friday_1600_bkk, 2 * 3600)  # 1h Friday + 1h Monday
    assert due == datetime(2026, 11, 16, 2, 0)  # Monday 09:00 Bangkok
    assert calendar.seconds(friday_1600_bkk, due) == 2 * 3600


def create(client, data, subject, impact, **extra):
    result = client.post('/api/v1/tickets', json=dict(
        data, subject=subject, channel='phone', impact_scope=impact, **extra))
    assert result.status_code == 201, result.text
    return result.json()


def test_queue_filters_orders_by_sla_and_resolves_names(capture):
    client, _, factory, data, _ = capture
    with factory() as db:
        configure_policy(db)
    critical = create(client, data, 'Whole exam room down', 'organization',
                      severity='S1', severity_overridden_reason='Exam blocked for everyone')
    question = create(client, data, 'How to export scores', 'non_disruptive')

    page = client.get('/api/v1/case-queue', params={'sort': 'sla', 'limit': 100}).json()
    ids = [row['id'] for row in page['items']]
    assert page['total'] >= 2
    assert ids.index(critical['id']) < ids.index(question['id'])  # S1 is due first
    row = next(item for item in page['items'] if item['id'] == critical['id'])
    assert row['customer'] and row['product']
    assert row['sla']['due_at'] is not None

    only_s1 = client.get('/api/v1/case-queue', params=[('severity', 'S1'), ('limit', 100)]).json()
    assert {item['severity'] for item in only_s1['items']} == {'S1'}
    found = client.get('/api/v1/case-queue', params={'q': 'export scores'}).json()
    assert [item['id'] for item in found['items']] == [question['id']]
    assert client.get('/api/v1/case-queue', params={'scope': 'unassigned', 'limit': 1}).json()['total'] >= 2

    with factory() as db:  # an overdue case must count as breached, not as safe
        ticket = db.get(Ticket, question['id'])
        ticket.sla_due_at = ticket.sla_risk_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    breached = client.get('/api/v1/case-queue', params=[('sla', 'breached'), ('limit', 100)]).json()
    assert question['id'] in [item['id'] for item in breached['items']]
    assert client.get('/api/v1/tickets/queue-summary').json()['sla_at_risk'] >= 1
