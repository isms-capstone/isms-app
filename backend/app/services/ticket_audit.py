"""Record persisted ticket changes in the same transaction as the mutation."""
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from app.db.models.ticket import Ticket
from app.db.models.work_category import TicketAudit


AUDITED_FIELDS = ('status', 'severity', 'owner_id', 'assignee_id', 'category_id')


@event.listens_for(Session, 'before_flush')
def audit_ticket_updates(session, _context, _instances):
    if any(isinstance(row, Ticket) for row in session.deleted):
        raise ValueError('Tickets must be cancelled with a reason')
    for ticket in session.dirty:
        if not isinstance(ticket, Ticket):
            continue
        state = inspect(ticket)
        changes = {}
        for field in AUDITED_FIELDS:
            history = state.attrs[field].history
            if not history.has_changes():
                continue
            old = history.deleted[0] if history.deleted else session.scalar(
                select(getattr(Ticket, field)).where(Ticket.id == ticket.id)
            )
            new = getattr(ticket, field)
            if old != new:
                changes[field] = {'old': old, 'new': new}
        if changes:
            session.add(TicketAudit(ticket_id=ticket.id,
                                    actor_id=session.info.get('ticket_actor_id'),
                                    event='ticket_fields_updated', changes=changes))


@event.listens_for(Session, 'do_orm_execute')
def reject_ticket_bulk_delete(state):
    if state.is_delete and state.statement.table.name == Ticket.__tablename__:
        raise ValueError('Tickets must be cancelled with a reason')
