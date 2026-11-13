"""Staff WRK/CAT APIs. External delivery adapters are separate integration work."""
from datetime import date, datetime, time, timezone
from typing import Literal

from app.api.deps import RoleChecker, require_admin
from app.api.v1.endpoints.customers import get_record
from app.api.v1.endpoints.product_configuration import product_case_options
from app.api.v1.endpoints.tickets import capture_values, commit_edit
from app.db.models.customer_context import ExamWindow
from app.db.models.master_data import CauseCode, SolutionCode, TicketType
from app.db.models.product import ProductInstance
from app.db.models.ticket import Ticket
from app.db.models.ticket_attachment import TicketAttachment
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.db.models.work_category import (
    CategoryUsage,
    TicketAudit,
    TicketTag,
    TicketWorklog,
)
from app.db.session import get_db
from app.schemas.categorization import CategorizationUpdate, Impact
from app.schemas.ticket import TicketCreate, TicketOut
from app.schemas.worklog import WorklogCreate
from app.services.categorization import (
    CATEGORY_FIELDS,
    record_categories,
    snapshot,
    suggest_severity,
)
from app.services.lifecycle import authorize_case, transition
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

staff = RoleChecker(['Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead'])
router = APIRouter(dependencies=[Depends(staff)])
Channel = Literal['line_oa', 'line_group', 'line_personal', 'portal', 'email', 'phone', 'face_to_face', 'other']


def utc(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()


def locked_ticket(db, ticket_id, user):
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None:
        raise HTTPException(404, 'Case not found')
    authorize_case(ticket, user)
    return ticket


def worklog_json(row, actor):
    return {'id': row.id, 'ticket_id': row.ticket_id, 'kind': row.kind, 'body': row.body,
            'channel': None if row.is_internal else row.channel, 'actor_id': row.actor_id, 'actor': actor,
            'message': row.body, 'is_internal': row.is_internal, 'author_id': row.actor_id,
            'created_at': utc(row.created_at)}


@router.post('/tickets/{ticket_id}/worklogs', status_code=201)
def create_worklog(ticket_id: int, body: WorklogCreate, db: Session = Depends(get_db), user=Depends(staff)):
    locked_ticket(db, ticket_id, user)
    row = TicketWorklog(ticket_id=ticket_id, actor_id=user.id, **body.model_dump())
    db.add(row)
    db.flush()
    db.add(TicketAudit(ticket_id=ticket_id, actor_id=user.id, event='worklog_created',
        changes={'worklog_id': row.id, 'kind': row.kind, 'channel': row.channel}, created_at=row.created_at))
    db.commit()
    actor = db.get(User, user.id)
    return worklog_json(row, actor.full_name or actor.username)


@router.get('/tickets/{ticket_id}/worklogs')
def worklogs(ticket_id: int, db: Session = Depends(get_db), offset: int = Query(0, ge=0),
             limit: int = Query(100, ge=1, le=500)):
    get_record(db, Ticket, ticket_id)
    rows = db.execute(select(TicketWorklog, User).join(User, User.id == TicketWorklog.actor_id)
        .where(TicketWorklog.ticket_id == ticket_id).order_by(TicketWorklog.created_at, TicketWorklog.id)
        .offset(offset).limit(limit)).all()
    return [worklog_json(row, actor.full_name or actor.username) for row, actor in rows]


@router.get('/tickets/{ticket_id}/audit')
def audit(ticket_id: int, db: Session = Depends(get_db), offset: int = Query(0, ge=0),
          limit: int = Query(100, ge=1, le=500)):
    get_record(db, Ticket, ticket_id)
    return [{'id': row.id, 'event': row.event, 'actor_id': row.actor_id,
             'created_at': utc(row.created_at), 'changes': row.changes}
        for row in db.scalars(select(TicketAudit).where(TicketAudit.ticket_id == ticket_id)
                              .order_by(TicketAudit.created_at, TicketAudit.id).offset(offset).limit(limit))]


@router.get('/tickets/{ticket_id}/timeline')
def timeline(ticket_id: int, db: Session = Depends(get_db), offset: int = Query(0, ge=0),
             limit: int = Query(100, ge=1, le=500)):
    ticket = get_record(db, Ticket, ticket_id)
    actors = {row.id: row.full_name or row.username for row in db.scalars(select(User))}
    events = [{'id': 'created', 'kind': 'case_created', 'created_at': utc(ticket.created_at),
               'actor_id': ticket.created_by_id, 'actor': actors.get(ticket.created_by_id), 'body': 'สร้างเคส'}]
    for row in db.scalars(select(TicketWorklog).where(TicketWorklog.ticket_id == ticket_id)):
        events.append(worklog_json(row, actors.get(row.actor_id)) | {'id': f'worklog-{row.id}'})
    for row in db.scalars(select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == ticket_id)):
        if (row.details or {}).get('event') == 'CASE_CREATED':
            continue  # Already represented by the unified case_created event.
        events.append({'id': f'status-{row.id}', 'kind': 'status_changed', 'created_at': utc(row.created_at),
            'actor_id': row.actor_id, 'actor': actors.get(row.actor_id),
            'body': f'{row.from_status} → {row.to_status}', 'details': row.details})
    audit_events = select(TicketAudit).where(or_(
        (TicketAudit.ticket_id == ticket_id) & (TicketAudit.event != 'worklog_created'),
        (TicketAudit.event == 'relationship_created')
        & (TicketAudit.changes['related_ticket_id'].as_integer() == ticket_id),
    ))
    for row in db.scalars(audit_events):
        incoming = row.event == 'relationship_created' and row.ticket_id != ticket_id
        changes = row.changes
        if incoming:
            changes = {**changes, 'related_ticket_id': row.ticket_id}
        description = {'similarity_decision': 'บันทึกการตัดสินใจจากเคสที่คล้ายกัน',
                       'request_start': 'เริ่มดำเนินคำขอ', 'request_fulfil': 'ส่งมอบผลคำขอ',
                       'request_confirm': 'ยืนยันและปิดคำขอ'}.get(row.event, 'บันทึกหมวดหมู่')
        events.append({'id': f'audit-{row.id}', 'kind': 'relationship_received' if incoming else row.event,
            'created_at': utc(row.created_at), 'actor_id': row.actor_id,
            'actor': actors.get(row.actor_id), 'body': description, 'changes': changes})
    for row in db.scalars(select(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id)):
        events.append({'id': f'attachment-{row.id}', 'kind': 'attachment', 'created_at': utc(row.created_at),
            'actor_id': row.uploaded_by_id, 'actor': actors.get(row.uploaded_by_id), 'body': row.original_name})
    def event_order(event):
        prefix, _, number = str(event['id']).partition('-')
        return event['created_at'], prefix, int(number) if number.isdigit() else 0
    events.sort(key=event_order)
    return {'items': events[offset:offset + limit], 'total': len(events)}


@router.get('/categorization/options')
def category_options(db: Session = Depends(get_db)):
    def options(model):
        return [{'id': row.id, 'name': row.name, **({'code': row.code} if hasattr(row, 'code') else {})}
                for row in db.scalars(select(model).where(model.is_active.is_(True)).order_by(model.name, model.id))]
    standard_types = ['Issues', 'Bugs', 'Request', 'Question', 'Export Data', 'Data Transfer', 'Data Recovery', 'Change Request']
    ticket_types = options(TicketType)
    ticket_types.sort(key=lambda row: standard_types.index(row['name']) if row['name'] in standard_types else len(standard_types))
    return {'ticket_types': ticket_types, 'causes': options(CauseCode), 'solutions': options(SolutionCode)}


@router.get('/categorization/severity-suggestion')
def severity_suggestion(impact_scope: Impact, is_exam_window: bool | None = None,
                        organization_id: int | None = Query(None, ge=1),
                        department_id: int | None = Query(None, ge=1), db: Session = Depends(get_db)):
    if is_exam_window is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        is_exam_window = bool(organization_id and db.scalar(select(ExamWindow.id).where(
            ExamWindow.organization_id == organization_id, ExamWindow.is_active.is_(True),
            ExamWindow.starts_at <= now, ExamWindow.ends_at > now,
            or_(ExamWindow.department_id.is_(None), ExamWindow.department_id == department_id)).limit(1)))
    return {'severity': suggest_severity(impact_scope, is_exam_window), 'is_exam_window': is_exam_window, 'rule': 'SRS 13.1'}


@router.get('/products/{product_id}/categorization-options')
def preferred_options(product_id: int, db: Session = Depends(get_db), user=Depends(staff)):
    result = product_case_options(product_id, db)
    masters = category_options(db)
    result.update(masters)
    counts = {(axis, option): count for axis, option, count in db.execute(
        select(CategoryUsage.axis, CategoryUsage.option_id, func.count()).where(
            CategoryUsage.user_id == user.id, CategoryUsage.product_id == product_id)
        .group_by(CategoryUsage.axis, CategoryUsage.option_id))}
    for key, axis in [('modules', 'module_id'), ('symptoms', 'symptom_id'),
                      ('service_stages', 'service_stage_id'), ('problem_types', 'category_id'),
                      ('ticket_types', 'ticket_type_id'), ('causes', 'root_cause_code_id'),
                      ('solutions', 'resolution_code_id')]:
        # Stable sort preserves catalogue ordering for equal frequencies.
        result[key].sort(key=lambda row: -counts.get((axis, row['id']), 0))
    return result


@router.get('/tickets/{ticket_id}/categorization')
def categorization(ticket_id: int, db: Session = Depends(get_db)):
    ticket = get_record(db, Ticket, ticket_id)
    instance = db.get(ProductInstance, ticket.product_instance_id) if ticket.product_instance_id else None
    case_type = db.get(TicketType, ticket.ticket_type_id) if ticket.ticket_type_id else None
    return snapshot(db, ticket) | {'product_id': instance.product_id if instance else None,
        'workflow': 'request' if case_type and case_type.name == 'Request' else 'incident',
        'suggested_severity': suggest_severity(ticket.impact_scope, ticket.is_exam_window) if ticket.impact_scope else None}


@router.patch('/tickets/{ticket_id}/categorization', response_model=TicketOut)
def update_categorization(ticket_id: int, body: CategorizationUpdate,
                          db: Session = Depends(get_db), user=Depends(staff)):
    ticket = locked_ticket(db, ticket_id, user)
    before = snapshot(db, ticket)
    changes = body.model_dump(exclude_unset=True)
    data = {field: getattr(ticket, field) for field in TicketCreate.model_fields
            if field not in ('save_as_draft', 'created_for_user_id', 'tags', 'similarity_feedback_id')}
    # CAT does not edit intake channel. Older records may contain legacy values
    # such as WEB; do not revalidate those against today's capture-only enum.
    data.update(tags=before['tags'], save_as_draft=True, channel=None,
                reported_at=ticket.reported_at.replace(tzinfo=timezone.utc))
    if changes.get('product_instance_id', ticket.product_instance_id) != ticket.product_instance_id:
        data.update(module_id=None, category_id=None, symptom_id=None, service_stage_id=None)
    elif changes.get('module_id', ticket.module_id) != ticket.module_id:
        data['category_id'] = None
    if 'severity' not in changes and any(key in changes for key in ('impact_scope', 'is_exam_window')):
        data.update(severity=None, severity_overridden_reason=None)
    data.update(changes)
    assessment_changed = bool(set(changes).intersection({'severity', 'impact_scope', 'is_exam_window',
                                                        'root_cause_code_id', 'resolution_code_id'}))
    values, _, _ = capture_values(TicketCreate.model_validate(data), db, validate_reported=False,
                                  allow_legacy_assessment=not assessment_changed)
    for key in CATEGORY_FIELDS:
        setattr(ticket, key, values[key])
    record_categories(db, ticket, user, data['tags'], before)
    return commit_edit(db, ticket)


@router.get('/categorization/popular-tags', dependencies=[Depends(require_admin)])
def popular_tags(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    count = func.count(TicketTag.ticket_id)
    return [{'name': name, 'ticket_count': total} for name, total in db.execute(
        select(TicketTag.name, count).group_by(TicketTag.name).order_by(count.desc(), TicketTag.name).limit(limit))]


class RequestAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['start', 'fulfil', 'confirm']
    assignee_id: int | None = Field(default=None, ge=1)
    fulfilment_detail: str | None = Field(default=None, max_length=20000)


@router.post('/tickets/{ticket_id}/request-workflow', response_model=TicketOut)
def request_workflow(ticket_id: int, body: RequestAction, db: Session = Depends(get_db), user=Depends(staff)):
    """Request has explicit fulfilment actions over the shared, audited CORE lifecycle."""
    ticket = locked_ticket(db, ticket_id, user)
    case_type = db.get(TicketType, ticket.ticket_type_id) if ticket.ticket_type_id else None
    if not case_type or case_type.name != 'Request':
        raise HTTPException(409, 'This workflow is only available for Request cases')
    changes = {'status': {'start': 'IN_PROGRESS', 'fulfil': 'RESOLVED', 'confirm': 'CLOSED'}[body.action]}
    if body.action == 'start' and body.assignee_id is not None:
        changes['assignee_id'] = body.assignee_id
    if body.action == 'fulfil':
        detail = (body.fulfilment_detail or '').strip()
        if not detail:
            raise HTTPException(422, 'Describe the delivered service before fulfilling the request')
        changes['resolution_detail'] = detail
    transition(db, ticket, changes, user)
    db.add(TicketAudit(ticket_id=ticket_id, actor_id=user.id, event='request_' + body.action,
                       changes={'action': body.action, 'status': changes['status']}))
    return commit_edit(db, ticket)


@router.get('/admin/audit-log', dependencies=[Depends(require_admin)])
def search_audit(
    db: Session = Depends(get_db),
    q: str = Query('', max_length=255),
    start: date | None = None,
    end: date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    if start and end and start > end:
        raise HTTPException(422, 'Start date must be before end date')
    query = (select(TicketAudit, Ticket.ticket_no, User.username)
             .join(Ticket, Ticket.id == TicketAudit.ticket_id)
             .outerjoin(User, User.id == TicketAudit.actor_id))
    if q := q.strip():
        query = query.where(or_(
            Ticket.ticket_no.contains(q, autoescape=True),
            User.username.contains(q, autoescape=True),
            TicketAudit.event.contains(q, autoescape=True),
            cast(TicketAudit.changes, String).contains(q, autoescape=True),
        ))
    if start:
        query = query.where(TicketAudit.created_at >= datetime.combine(start, time.min))
    if end:
        query = query.where(TicketAudit.created_at <= datetime.combine(end, time.max))
    results = db.execute(query.order_by(TicketAudit.created_at.desc(), TicketAudit.id.desc())
                         .offset(offset).limit(limit + 1)).all()
    return {
        'has_more': len(results) > limit,
        'rows': [
            {'id': row.id, 'ticket_id': row.ticket_id, 'ticket_no': number,
             'actor': username, 'actor_id': row.actor_id, 'event': row.event,
             'changes': row.changes, 'created_at': utc(row.created_at)}
            for row, number, username in results[:limit]
        ],
    }
