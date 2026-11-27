"""One transaction-safe mutation path for CAP and CORE lifecycle APIs."""
from app.core.labels import field_label
from datetime import datetime, timezone
from fastapi import HTTPException
from app.core.state_machine import validate_status_transition
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.db.models.master_data import CauseCode, SolutionCode, ProblemType
from app.db.models.product import ProductInstance


SUPPORT_ROLES = {'Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead'}
# SRS 3.2: Developer may update a case but may not close, cancel or merge it.
CLOSING_STATUSES = {'RESOLVED', 'CLOSED', 'CANCELLED', 'DUPLICATE'}
HISTORY_ONLY_FIELDS = {'status', 'reopen_reason', 'pending_external_checked', 'pending_external_expected'}


def authorize_view(ticket, user):
    """อ่าน/ขอข้อมูลประกอบของเคสได้ แค่ต้องมี support role ใดก็ได้
    ไม่บังคับว่าต้องเป็น creator/owner/assignee ของเคสนั้นโดยเฉพาะ
    ใช้กับ endpoint ที่แค่ "ดู" เช่น lifecycle-options, ticket detail
    ไม่ใช้กับ endpoint ที่ "แก้ไข" เคส (ใช้ authorize_case แทน)
    """
    role = user.role.name if user.role else None
    if role not in SUPPORT_ROLES:
        raise HTTPException(403, 'บัญชีนี้ไม่มีสิทธิ์ดำเนินการกับเคส')


def authorize_case(ticket, user):
    """แก้ไข/เปลี่ยนสถานะเคสได้ ต้องเป็น Admin หรือ participant ของเคสนั้นเท่านั้น
    คงพฤติกรรมเดิมไว้ทั้งหมด — ใช้กับทุก endpoint ที่ mutate เคส
    """
    role = user.role.name if user.role else None
    if role not in SUPPORT_ROLES:
        raise HTTPException(403, 'บัญชีนี้ไม่มีสิทธิ์ดำเนินการกับเคส')
    if role == 'Admin' or user.id in (ticket.created_by_id, ticket.owner_id, ticket.assignee_id):
        return
    raise HTTPException(403, 'แก้ไขเคสนี้ได้เฉพาะผู้ที่เกี่ยวข้องกับเคสหรือผู้ดูแลระบบ')


def transition(db, ticket, changes, user):
    authorize_case(ticket, user)
    from app.services.categorization import CATEGORY_FIELDS, snapshot, record_categories
    category_before = snapshot(db, ticket) if set(changes).intersection(CATEGORY_FIELDS) else None
    target = changes['status']
    data = {name: getattr(ticket, name, None) for name in (
        'organization_id', 'contact_id', 'subject', 'channel', 'assignee_id',
        'category_id', 'module_id', 'root_cause_code_id', 'resolution_code_id', 'resolution_detail',
        'product_instance_id', 'master_ticket_id', 'closed_at', 'resolved_at',
        'pending_external_reason', 'cancel_reason')}
    data.update({key: value for key, value in changes.items() if value is not None})
    if target == ticket.status:
        raise HTTPException(409, 'เคสอยู่ในสถานะนี้อยู่แล้ว')
    role = user.role.name
    if role == 'Developer' and target in CLOSING_STATUSES:
        raise HTTPException(403, 'ทีมพัฒนา (Tier 0) ปิดหรือยกเลิกเคสไม่ได้ ให้ส่งเคสกลับพร้อมผลการตรวจสอบ')
    if target == 'RESOLVED' and not has_customer_reply(db, ticket.id):
        # BR-05: a case is finished only after the customer heard back at least once.
        raise HTTPException(422, 'ก่อนบันทึกว่าแก้ไขเสร็จ ต้องตอบลูกค้าอย่างน้อย 1 ครั้ง (ข้อความถึงลูกค้า)')
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
                raise HTTPException(422, f'ไม่พบ{field_label(field)} หรือถูกปิดใช้งาน')
            if field == 'product_instance_id' and row.organization_id != ticket.organization_id:
                raise HTTPException(422, 'ระบบที่เลือกเป็นของลูกค้ารายอื่น')
    if 'assignee_id' in changes and changes['assignee_id'] != ticket.assignee_id:
        from app.services.routing import target_user, lead_for, route_team
        self_pick = ticket.status == 'NEW' and ticket.assignee_id is None and changes['assignee_id'] == user.id
        if not self_pick and not lead_for(db, user, route_team(db, ticket)):
            raise HTTPException(403, 'การมอบหมายเคสทำได้โดยหัวหน้าทีมที่รับผิดชอบเท่านั้น')
        target_user(db, ticket, changes['assignee_id'], ticket.current_tier if ticket.current_tier is not None else 2)
    if target == 'RESOLVED' or set(changes).intersection({'category_id', 'module_id', 'product_instance_id'}):
        from app.api.v1.endpoints.product_configuration import CaseOptionsSelection, validate_selection
        instance = db.get(ProductInstance, data.get('product_instance_id')) if data.get('product_instance_id') else None
        if instance:
            validate_selection(instance.product_id, CaseOptionsSelection(
                module_id=data.get('module_id'), symptom_id=ticket.symptom_id,
                service_stage_id=ticket.service_stage_id, problem_type_id=data.get('category_id')), db)
        elif data.get('category_id'):
            raise HTTPException(422, 'กรุณาเลือกระบบของลูกค้าก่อนเลือกหมวดหมู่')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    from app.services import sla_engine

    if target == 'PENDING_CUSTOMER' and not (changes.get('pending_customer_reason') or '').strip():
        raise HTTPException(422, 'กรุณาระบุว่ากำลังรออะไรจากลูกค้า')
    if target == 'CLOSED' and sla_engine.update_breach(db, ticket, now):
        if not (changes.get('sla_breach_reason') or ticket.sla_breach_reason or '').strip():
            raise HTTPException(422, 'เคสนี้เกิน SLA กรุณาระบุเหตุผลก่อนปิดเคส')
    if target != 'PENDING_CUSTOMER':
        changes.pop('pending_customer_reason', None)
    if target != 'CLOSED':
        changes.pop('sla_breach_reason', None)
    sla_engine.sync_clock(db, ticket, now)
    if target == 'DUPLICATE':
        from app.services.ticket_relationships import close_linked_case, lock_pair, move_duplicate_data

        ticket, master = lock_pair(db, ticket.id, data['master_ticket_id'])
        authorize_case(master, user)
        move_duplicate_data(db, ticket, master, user.id, 'Duplicate status action')
        if master.status == 'CLOSED':
            close_linked_case(db, ticket, master, 'DUPLICATE', user.id, now)
        return ticket
    history = TicketStatusHistory(ticket_id=ticket.id, from_status=ticket.status,
        to_status=target, actor_id=user.id, created_at=now,
        details={key: value for key, value in changes.items() if key != 'status' and value is not None})
    db.add(history)
    for key, value in changes.items():
        if value is not None and key not in HISTORY_ONLY_FIELDS:
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
    if target == 'CLOSED':
        from app.services.ticket_relationships import close_relationships
        ticket.closed_at = now
        close_relationships(db, ticket, user.id, now)
    if target == 'REOPENED': ticket.reopen_count += 1
    if target == 'NEW' or 'product_instance_id' in changes:
        sla_engine.apply_exam_window(db, ticket, now)
    sla_engine.sync_clock(db, ticket, now)
    sla_engine.update_breach(db, ticket, now)
    from app.services.routing import assign_responsible_team
    assign_responsible_team(db, ticket, user.id, now)
    if category_before is not None:
        record_categories(db, ticket, user, category_before['tags'], category_before)
    return ticket


def has_customer_reply(db, ticket_id):
    from sqlalchemy import select
    from app.db.models.work_category import TicketWorklog
    return db.scalar(select(TicketWorklog.id).where(
        TicketWorklog.ticket_id == ticket_id, TicketWorklog.is_internal.is_(False)).limit(1)) is not None


def record_first_response(db, ticket, at):
    """SRS 7.2 / KPI-03: first response is the first message the customer receives."""
    if ticket.first_response_at is not None:
        return False
    from app.services import sla_engine
    ticket.first_response_at = at
    sla_engine.sync_clock(db, ticket, at)
    sla_engine.update_breach(db, ticket, at)
    return True
