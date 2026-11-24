import pytest
from sqlalchemy import delete, select

from app.db.models.ticket import Ticket
from app.db.models.work_category import TicketAudit
from test_tickets import capture


def test_ticket_audit_and_cancellation(capture):
    client, _, factory, context, _ = capture
    created = client.post('/api/v1/tickets', json={
        **context, 'subject': 'AUD acceptance', 'channel': 'phone',
        'impact_scope': 'organization', 'is_exam_window': True,
    })
    assert created.status_code == 201, created.text
    ticket = created.json()
    path = f"/api/v1/tickets/{ticket['id']}"
    assert client.delete(path).status_code == 405
    with factory() as db:
        row = db.get(Ticket, ticket['id'])
        db.delete(row)
        with pytest.raises(ValueError, match='cancelled'):
            db.flush()
        db.rollback()
        with pytest.raises(ValueError, match='cancelled'):
            db.execute(delete(Ticket).where(Ticket.id == ticket['id']))
        db.info['ticket_actor_id'] = ticket['created_by_id']
        row = db.get(Ticket, ticket['id'])
        row.severity = 'S2'
        row.assignee_id = ticket['created_by_id']
        row.category_id = None
        db.commit()
        event = db.scalar(select(TicketAudit).where(
            TicketAudit.ticket_id == row.id, TicketAudit.event == 'ticket_fields_updated'))
        assert event.actor_id == ticket['created_by_id']
        assert event.created_at
        assert event.changes == {
            'severity': {'old': 'S1', 'new': 'S2'},
            'assignee_id': {'old': None, 'new': ticket['created_by_id']},
            'category_id': {'old': context['category_id'], 'new': None},
        }
    assert client.patch(path + '/status', json={
        'status': 'CANCELLED', 'cancel_reason': '   ',
    }).status_code == 422
    cancelled = client.patch(path + '/status', json={
        'status': 'CANCELLED', 'cancel_reason': 'Duplicate test intake',
    })
    assert cancelled.status_code == 200, cancelled.text
    assert client.get(path).json()['status'] == 'CANCELLED'
