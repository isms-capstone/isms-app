"""SLA acceptance cases across calendar, lifecycle and scheduler."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.sla_calendar import Schedule
from app.db.init_db import DEFAULT_SLA_POLICY, DEFAULT_SLA_RULES
from app.db.models.master_data import SlaPolicy, SlaPolicyRule
from app.db.models.routing import RoutingNotification
from app.db.models.sla import SlaClock
from app.db.models.ticket import Ticket
from app.services.sla_engine import measurement, run_sla_checks, sync_clock
from test_tickets import capture  # noqa: F401


def test_calendar_skips_weekend_and_local_holiday():
    calendar = Schedule(holidays=frozenset({date(2026, 11, 16)}))
    friday_1630 = datetime(2026, 11, 13, 9, 30)
    tuesday_0830 = datetime(2026, 11, 17, 1, 30)
    assert calendar.seconds(friday_1630, tuesday_0830) == 3600


def configure_policy(db):
    policy = db.scalar(select(SlaPolicy).where(SlaPolicy.name == DEFAULT_SLA_POLICY["name"]))
    if not policy:
        policy = SlaPolicy(**DEFAULT_SLA_POLICY)
        db.add(policy)
        db.flush()
        db.add_all(SlaPolicyRule(sla_policy_id=policy.id, **rule) for rule in DEFAULT_SLA_RULES)
    db.commit()


def test_separate_clocks_pause_and_notifications(capture):
    client, _, factory, data, _ = capture
    with factory() as db:
        configure_policy(db)
    result = client.post('/api/v1/tickets', json=dict(
        data, subject='SLA clock', channel='phone', impact_scope='organization',
        severity='S1', severity_overridden_reason='All customers affected',
    ))
    assert result.status_code == 201, result.text
    ticket_id = result.json()['id']
    with factory() as db:
        ticket = db.get(Ticket, ticket_id)
        start = ticket.reported_at
        ticket.first_response_at = start + timedelta(minutes=16)
        ticket.status = 'PENDING_CUSTOMER'
        ticket.pending_customer_reason = 'Request logs'
        sync_clock(db, ticket, start + timedelta(minutes=20))
        db.commit()
        state = measurement(db, ticket, start + timedelta(days=5))
        assert state['paused']
        assert state['first_response']['elapsed_seconds'] == 16 * 60
        assert state['first_response']['breached']
        assert state['resolution']['elapsed_seconds'] == 20 * 60
        assert state['remaining_seconds'] is None
        now = start + timedelta(days=10)
        assert run_sla_checks(db, now) >= 1
        assert run_sla_checks(db, now) == 0
        assert db.scalar(select(RoutingNotification.id).where(
            RoutingNotification.ticket_id == ticket_id,
            RoutingNotification.kind == 'sla_customer_followup',
        ))
        ticket = db.get(Ticket, ticket_id)
        ticket.status = 'IN_PROGRESS'
        sync_clock(db, ticket, now)
        db.commit()
        assert run_sla_checks(db, now + timedelta(hours=6)) >= 3
        assert run_sla_checks(db, now + timedelta(hours=6)) == 0
        assert [row.status for row in db.scalars(select(SlaClock).where(
            SlaClock.ticket_id == ticket_id).order_by(SlaClock.id))] == [
                'NEW', 'PENDING_CUSTOMER', 'IN_PROGRESS']


def test_pending_and_close_require_reasons(capture):
    client, _, factory, data, _ = capture
    created = client.post('/api/v1/tickets', json=dict(data, subject='Closure', channel='phone')).json()
    url = f"/api/v1/tickets/{created['id']}/status"
    with factory() as db:
        ticket = db.get(Ticket, created['id'])
        ticket.status = 'IN_PROGRESS'
        db.commit()
    assert client.patch(url, json={'status': 'PENDING_CUSTOMER'}).status_code == 422
    result = client.patch(url, json={'status': 'PENDING_CUSTOMER', 'pending_customer_reason': 'Need logs'})
    assert result.status_code == 200, result.text
    assert result.json()['pending_customer_reason'] == 'Need logs'
    with factory() as db:
        ticket = db.get(Ticket, created['id'])
        ticket.status = 'RESOLVED'
        ticket.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        ticket.sla_breached = True
        db.commit()
    assert client.patch(url, json={'status': 'CLOSED'}).status_code == 422
    result = client.patch(url, json={'status': 'CLOSED', 'sla_breach_reason': 'Upstream outage'})
    assert result.status_code == 200, result.text
    assert result.json()['sla_breach_reason'] == 'Upstream outage'

def test_exam_priority_is_raised_once_and_notified(capture):
    from app.db.models.customer_context import ExamWindow

    client, _, factory, data, _ = capture
    now = datetime.now(timezone.utc)
    with factory() as db:
        db.add(ExamWindow(
            organization_id=data['organization_id'], name='Live exam',
            starts_at=(now - timedelta(hours=2)).replace(tzinfo=None),
            ends_at=(now + timedelta(hours=2)).replace(tzinfo=None),
        ))
        db.commit()
    created = client.post('/api/v1/tickets', json=dict(
        data, subject='Live exam issue', channel='phone', impact_scope='single_user',
        reported_at=(now - timedelta(minutes=30)).isoformat(),
    ))
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket['severity'] == 'S2'
    path = f"/api/v1/tickets/{ticket['id']}/reported-at"
    adjusted = client.patch(path, json={'reported_at': (now - timedelta(minutes=25)).isoformat()})
    assert adjusted.status_code == 200, adjusted.text
    assert adjusted.json()['severity'] == 'S2'
    with factory() as db:
        alerts = db.scalars(select(RoutingNotification).where(
            RoutingNotification.ticket_id == ticket['id'],
            RoutingNotification.kind == 'sla_exam_upgrade',
        )).all()
        assert len(alerts) == 1
    adjusted = client.patch(path, json={'reported_at': (now - timedelta(hours=3)).isoformat()})
    assert adjusted.status_code == 200, adjusted.text
    assert adjusted.json()['severity'] == 'S3'

def test_warning_thresholds_and_s1_outside_business_hours(capture):
    client, _, factory, data, _ = capture
    with factory() as db:
        configure_policy(db)
    result = client.post('/api/v1/tickets', json=dict(
        data, subject='Threshold test', channel='phone', impact_scope='organization',
        severity='S1', severity_overridden_reason='Critical incident',
    ))
    assert result.status_code == 201, result.text
    ticket_id = result.json()['id']
    start = datetime(2026, 11, 15, 0, 0)  # Sunday, UTC.
    with factory() as db:
        ticket = db.get(Ticket, ticket_id)
        ticket.reported_at = start
        sync_clock(db, ticket, start)
        db.commit()
        for seconds, expected in ((449, 0), (450, 1), (675, 1), (900, 0), (901, 1)):
            now = start + timedelta(seconds=seconds)
            assert run_sla_checks(db, now) == expected
            assert run_sla_checks(db, now) == 0
        assert db.get(Ticket, ticket_id).sla_breached

def test_worker_notifies_breach_after_resolution(capture):
    client, _, factory, data, _ = capture
    with factory() as db:
        configure_policy(db)
    result = client.post('/api/v1/tickets', json=dict(
        data, subject='Resolved before worker', channel='phone', impact_scope='organization',
        severity='S1', severity_overridden_reason='Critical incident',
    ))
    assert result.status_code == 201, result.text
    ticket_id = result.json()['id']
    with factory() as db:
        ticket = db.get(Ticket, ticket_id)
        ticket.resolved_at = ticket.reported_at + timedelta(hours=6)
        ticket.status = 'RESOLVED'
        sync_clock(db, ticket, ticket.resolved_at)
        now = ticket.resolved_at + timedelta(minutes=1)
        db.commit()
        assert run_sla_checks(db, now) > 0
        assert run_sla_checks(db, now) == 0
        assert db.get(Ticket, ticket_id).sla_breached
