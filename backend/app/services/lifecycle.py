"""One transaction-safe mutation path for CAP and CORE lifecycle APIs."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.state_machine import validate_status_transition
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.db.models.master_data import CauseCode, SolutionCode, ProblemType
from app.db.models.product import ProductInstance


def authorize_case(ticket, user):
    role = user.role.name if user.role else None
    if role not in {'Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead'}:
        raise HTTPException(403, 'Case operations require a support role')
    if role == 'Admin' or user.id in (ticket.created_by_id, ticket.owner_id, ticket.assignee_id):
        return
    raise HTTPException(403, 'Only Admin or a case participant can change this case')


def transition(db, ticket, changes, user):
    authorize_case(ticket, user)
    target = changes['status']
    data = {name: getattr(ticket, name, None) for name in (
        'organization_id', 'contact_id', 'subject', 'channel', 'assignee_id',
        'category_id', 'root_cause_code_id', 'resolution_code_id', 'resolution_detail',
        'product_instance_id', 'master_ticket_id', 'closed_at', 'resolved_at',
        'pending_external_reason', 'cancel_reason')}
    data.update({key: value for key, value in changes.items() if value is not None})
    if target == ticket.status:
        raise HTTPException(409, 'The case is already in this status')
    role = user.role.name
    policy_role = 'Agent' if role in {'Specialist', 'Developer', 'Team Lead'} else role
    validate_status_transition(ticket.status, target, policy_role, data)
    for field, model in [('assignee_id', User), ('root_cause_code_id', CauseCode),
                         ('resolution_code_id', SolutionCode), ('category_id', ProblemType),
                         ('product_instance_id', ProductInstance)]:
        if data.get(field) is not None and (field in changes or target == 'RESOLVED'):
            row = db.get(model, data[field])
            if row is None or not row.is_active:
                raise HTTPException(422, f'{field} is missing or inactive')
            if field == 'product_instance_id' and row.organization_id != ticket.organization_id:
                raise HTTPException(422, 'Product instance belongs to another customer')
    if 'assignee_id' in changes and changes['assignee_id'] != ticket.assignee_id:
        from app.services.routing import target_user, lead_for, route_team
        self_pick = ticket.status == 'NEW' and ticket.assignee_id is None and changes['assignee_id'] == user.id
        if not self_pick and not lead_for(db, user, route_team(db, ticket)):
            raise HTTPException(403, 'Manual assignment requires the responsible team lead')
        target_user(db, ticket, changes['assignee_id'], ticket.current_tier if ticket.current_tier is not None else 2)
    if target == 'DUPLICATE':
        master = db.get(Ticket, data['master_ticket_id'])
        if not master or master.id == ticket.id or master.status in {'DRAFT', 'DUPLICATE', 'CANCELLED'}:
            raise HTTPException(422, 'Select a different published master case')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    history = TicketStatusHistory(ticket_id=ticket.id, from_status=ticket.status,
        to_status=target, actor_id=user.id, created_at=now,
        details={key: value for key, value in changes.items() if key != 'status' and value is not None})
    db.add(history)
    for key, value in changes.items():
        if value is not None and key not in {'status', 'reopen_reason'}:
            setattr(ticket, key, value)
    from app.services.routing import close_interval, initialize_interval
    if target in {'RESOLVED', 'CLOSED', 'DUPLICATE', 'CANCELLED'}:
        close_interval(db, ticket, now)
    ticket.status = target
    ticket.routing_version += 1
    if target in {'NEW', 'REOPENED', 'IN_PROGRESS'}:
        if ticket.current_tier is None: ticket.current_tier = getattr(user, 'default_tier', 2)
        db.flush()
        initialize_interval(db, ticket, now, history.id)
    if target == 'RESOLVED': ticket.resolved_at = now
    if target == 'CLOSED': ticket.closed_at = now
    if target == 'REOPENED': ticket.reopen_count += 1
    if target == 'IN_PROGRESS' and ticket.first_response_at is None: ticket.first_response_at = now
    return ticket
