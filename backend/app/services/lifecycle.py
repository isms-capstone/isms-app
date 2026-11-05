"""One transaction-safe mutation path for CAP and CORE lifecycle APIs."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.state_machine import validate_status_transition
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.db.models.master_data import CauseCode, SolutionCode, ProblemType
from app.db.models.product import ProductInstance


SUPPORT_ROLES = {'Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead'}


def authorize_view(ticket, user):
    """อ่าน/ขอข้อมูลประกอบของเคสได้ แค่ต้องมี support role ใดก็ได้
    ไม่บังคับว่าต้องเป็น creator/owner/assignee ของเคสนั้นโดยเฉพาะ
    ใช้กับ endpoint ที่แค่ "ดู" เช่น lifecycle-options, ticket detail
    ไม่ใช้กับ endpoint ที่ "แก้ไข" เคส (ใช้ authorize_case แทน)
    """
    role = user.role.name if user.role else None
    if role not in SUPPORT_ROLES:
        raise HTTPException(403, 'Case operations require a support role')


def authorize_case(ticket, user):
    """แก้ไข/เปลี่ยนสถานะเคสได้ ต้องเป็น Admin หรือ participant ของเคสนั้นเท่านั้น
    คงพฤติกรรมเดิมไว้ทั้งหมด — ใช้กับทุก endpoint ที่ mutate เคส
    """
    role = user.role.name if user.role else None
    if role not in SUPPORT_ROLES:
        raise HTTPException(403, 'Case operations require a support role')
    if role == 'Admin' or user.id in (ticket.created_by_id, ticket.owner_id, ticket.assignee_id):
        return
    raise HTTPException(403, 'Only Admin or a case participant can change this case')


def transition(db, ticket, changes, user):
    authorize_case(ticket, user)
    from app.services.categorization import CATEGORY_FIELDS, snapshot, record_categories
    category_before = snapshot(db, ticket) if set(changes).intersection(CATEGORY_FIELDS) else None
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
    if ticket.status == 'DRAFT' and target == 'NEW':
        from types import SimpleNamespace
        from app.services.similarity_decisions import require_publish_decision
        require_publish_decision(db, SimpleNamespace(id=ticket.id, subject=data['subject'],
            description=ticket.description, organization_id=data['organization_id'],
            product_instance_id=data['product_instance_id']))
    for field, model in [('assignee_id', User), ('root_cause_code_id', CauseCode),
                         ('resolution_code_id', SolutionCode), ('category_id', ProblemType),
                         ('product_instance_id', ProductInstance)]:
        if data.get(field) is not None and (field in changes or target == 'RESOLVED'):
            row = db.get(model, data[field])
            if row is None or not row.is_active:
                raise HTTPException(422, f'{field} is missing or inactive')
            if field == 'product_instance_id' and row.organization_id != ticket.organization_id:
                raise HTTPException(422, 'Product instance belongs to another customer')
    if set(changes).intersection({'category_id', 'product_instance_id'}):
        from app.api.v1.endpoints.product_configuration import CaseOptionsSelection, validate_selection
        instance = db.get(ProductInstance, data.get('product_instance_id')) if data.get('product_instance_id') else None
        if instance:
            validate_selection(instance.product_id, CaseOptionsSelection(
                module_id=ticket.module_id, symptom_id=ticket.symptom_id,
                service_stage_id=ticket.service_stage_id, problem_type_id=data.get('category_id')), db)
        elif data.get('category_id'):
            raise HTTPException(422, 'Select a product instance before category options')
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
    ticket.status = target
    if target == 'RESOLVED': ticket.resolved_at = now
    if target == 'CLOSED': ticket.closed_at = now
    if target == 'REOPENED': ticket.reopen_count += 1
    if target == 'IN_PROGRESS' and ticket.first_response_at is None: ticket.first_response_at = now
    if category_before is not None:
        record_categories(db, ticket, user, category_before['tags'], category_before)
    return ticket
