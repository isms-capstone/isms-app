import pytest
from datetime import datetime, timedelta
from app.core.working_days import add_business_days, is_auto_close_eligible
from test_tickets import capture  # noqa: F401

def test_add_business_days_skips_weekends():
    # วันศุกร์ที่ 9 ต.ค. + 3 วันทำการ -> ศุกร์(1) -> จันทร์(2) -> อังคาร(3) -> พุธที่ 14 ต.ค.
    friday = datetime(2026, 10, 9, 10, 0, 0)
    expected_wednesday = datetime(2026, 10, 14, 10, 0, 0)
    
    result = add_business_days(friday, 3)
    assert result == expected_wednesday

def test_auto_close_eligibility():
    resolved_at = datetime(2026, 10, 12, 10, 0, 0) # วันจันทร์
    
    # ยังไม่ครบ 3 วันทำการ (วันพุธ) -> False
    current_wednesday = datetime(2026, 10, 14, 10, 0, 0)
    assert is_auto_close_eligible(resolved_at, current_wednesday, 3) is False
    
    # ครบ 3 วันทำการพอดี (วันพฤหัสบดี) -> True
    current_thursday = datetime(2026, 10, 15, 10, 0, 0)
    assert is_auto_close_eligible(resolved_at, current_thursday, 3) is True

def test_calendar_business_days_skip_holidays():
    from datetime import date
    from app.core.sla_calendar import Schedule
    calendar = Schedule(holidays=frozenset({date(2026, 11, 16)}))  # Monday holiday
    friday_10_bkk = datetime(2026, 11, 13, 3, 0)  # UTC
    # Mon is a holiday, so 3 working days are Tue, Wed, Thu.
    assert calendar.add_business_days(friday_10_bkk, 3) == datetime(2026, 11, 19, 3, 0)


def test_worker_closes_resolved_cases_and_flags_breaches(capture):
    from datetime import timedelta
    from sqlalchemy import select
    from app.db.models.routing import RoutingNotification, RoutingPolicy
    from app.db.models.ticket import Ticket
    from app.services.auto_close import run_auto_close_resolved_tickets

    client, _, factory, data, _ = capture
    subjects = ('Printer jammed at registry desk', 'Projector colour wrong in hall', 'Scanner rejects badge cards')
    ids = []
    for subject in subjects:
        created = client.post('/api/v1/tickets', json=dict(data, subject=subject, channel='phone'))
        assert created.status_code == 201, created.text
        ids.append(created.json()['id'])
    with factory() as db:
        db.merge(RoutingPolicy(id=1, s1_minutes=15, enabled=True, auto_close_business_days=2))
        now = datetime(2026, 11, 20, 3, 0)  # Friday 10:00 Bangkok
        for ticket_id, resolved in zip(ids, (now - timedelta(days=4), now - timedelta(hours=2), now - timedelta(days=4))):
            ticket = db.get(Ticket, ticket_id)
            ticket.status, ticket.resolved_at = 'RESOLVED', resolved
        breached = db.get(Ticket, ids[2])
        breached.sla_breached, breached.owner_id = True, breached.created_by_id
        db.commit()
        assert run_auto_close_resolved_tickets(db, now=now) == 1
        statuses = {ticket_id: db.get(Ticket, ticket_id).status for ticket_id in ids}
        assert statuses == {ids[0]: 'CLOSED', ids[1]: 'RESOLVED', ids[2]: 'RESOLVED'}
        alert = db.scalar(select(RoutingNotification).where(RoutingNotification.ticket_id == ids[2]))
        assert alert and alert.kind == 'auto_close_blocked'
        assert run_auto_close_resolved_tickets(db, now=now) == 0  # idempotent, alert not repeated
        assert len(db.scalars(select(RoutingNotification).where(RoutingNotification.ticket_id == ids[2])).all()) == 1
