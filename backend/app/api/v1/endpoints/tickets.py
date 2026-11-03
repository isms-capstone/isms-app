"""Minimal case capture; lifecycle transitions belong to the lifecycle tasks."""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse

from pydantic import BaseModel, ConfigDict

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker, get_current_user
from app.api.v1.endpoints.customers import get_record
from app.api.v1.endpoints.product_configuration import CaseOptionsSelection, validate_selection
from app.core.state_machine import validate_status_transition
from app.db.models.customer import Contact, Organization
from app.db.models.customer_context import CourseOrExam, Department, ExamWindow
from app.db.models.master_data import (
    CauseCode,
    Product,
    SolutionCode,
    TicketType,
)
from app.db.models.product import ProductInstance
from app.db.models.ticket import OPEN_STATUSES, TICKET_STATUSES, Ticket, TicketNumberSequence
from app.db.models.ticket_attachment import TicketAttachment
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ticket import DraftFieldUpdate, ReportedTimeUpdate, TicketCreate, TicketOut, TicketResolve, TicketFollowUp
from app.db.models.ticket import TicketStatus
from app.services.auto_close import run_auto_close_resolved_tickets


router = APIRouter(dependencies=[Depends(get_current_user)])
require_capture = RoleChecker(['Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead'])


class TicketStatusUpdatePayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: TicketStatus
    assignee_id: int | None = None
    contact_id: int | None = None
    subject: str | None = None
    channel: str | None = None
    pending_external_reason: str | None = None
    category_id: int | None = None
    root_cause_code_id: int | None = None
    resolution_code_id: int | None = None
    resolution_detail: str | None = None
    product_instance_id: int | None = None
    reopen_reason: str | None = None
    master_ticket_id: int | None = None
    cancel_reason: str | None = None


def next_ticket_number(db: Session, now: datetime):
    """Atomic upsert holds the monthly row lock until the ticket commits."""
    # Thailand uses UTC+7 without daylight saving; portable on Windows too.
    period = now.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=7))).strftime('%Y%m')
    table = TicketNumberSequence.__table__
    if db.bind.dialect.name == 'mysql':
        from sqlalchemy.dialects.mysql import insert
        statement = insert(table).values(period=period, value=1)
        statement = statement.on_duplicate_key_update(value=table.c.value + 1)
    elif db.bind.dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
        statement = insert(table).values(period=period, value=1)
        statement = statement.on_conflict_do_update(index_elements=['period'], set_={'value': table.c.value + 1})
    else:
        raise RuntimeError('Ticket numbering requires MariaDB or SQLite')
    db.execute(statement)
    value = db.scalar(select(table.c.value).where(table.c.period == period).with_for_update())
    if value > 99999:
        raise HTTPException(409, 'Monthly ticket number capacity exceeded')
    return f'DVHT-{period}-{value:05d}'


def active_record(db, model, record_id):
    record = get_record(db, model, record_id)
    if not record.is_active:
        raise HTTPException(422, f'{model.__name__} is inactive')
    return record


def capture_values(body: TicketCreate, db: Session, validate_reported=True):
    values = body.model_dump()
    values.pop('save_as_draft')
    values.pop('created_for_user_id', None)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reported = body.reported_at.astimezone(timezone.utc).replace(tzinfo=None) if body.reported_at else now
    if validate_reported and (reported > now or reported < now - timedelta(days=7)):
        raise HTTPException(422, 'reported_at must be within the last 7 days')
    organization_id = body.organization_id
    if body.contact_id is not None:
        contact = active_record(db, Contact, body.contact_id)
        if organization_id is not None and contact.organization_id != organization_id:
            raise HTTPException(422, 'Contact belongs to another organization')
        organization_id = contact.organization_id
    if organization_id is not None:
        active_record(db, Organization, organization_id)
    for field, model in [('department_id', Department), ('course_or_exam_id', CourseOrExam),
                         ('product_instance_id', ProductInstance)]:
        record_id = getattr(body, field)
        if record_id is not None:
            record = active_record(db, model, record_id)
            if organization_id is None or record.organization_id != organization_id:
                raise HTTPException(422, f'{field} must belong to the selected organization')
    if body.ticket_type_id is not None:
        active_record(db, TicketType, body.ticket_type_id)
    selection = CaseOptionsSelection(module_id=body.module_id, symptom_id=body.symptom_id,
                                     service_stage_id=body.service_stage_id, problem_type_id=body.category_id)
    policy_id = None
    if body.product_instance_id is not None:
        instance = db.get(ProductInstance, body.product_instance_id)
        validate_selection(instance.product_id, selection, db)
        product = db.get(Product, instance.product_id)
        if product.sla_policy_id is not None:
            from app.db.models.master_data import SlaPolicy
            policy = db.get(SlaPolicy, product.sla_policy_id)
            policy_id = policy.id if policy and policy.is_active else None
    elif any(selection.model_dump().values()):
        raise HTTPException(422, 'Select a product instance before category options')
    exam = False
    if organization_id is not None:
        exam = db.scalar(select(ExamWindow.id).where(
            ExamWindow.organization_id == organization_id, ExamWindow.is_active.is_(True),
            ExamWindow.starts_at <= reported, ExamWindow.ends_at > reported,
            or_(ExamWindow.department_id.is_(None), ExamWindow.department_id == body.department_id)
        ).limit(1)) is not None
    complete = (not body.save_as_draft and organization_id is not None
                and body.subject is not None and body.channel is not None)
    values.update(organization_id=organization_id, reported_at=reported, created_at=now,
                  status='NEW' if complete else 'DRAFT',
                  sla_policy_id=policy_id, is_exam_window=exam)
    return values, complete, now


@router.post('/tickets', response_model=TicketOut, status_code=201)
def create_ticket(body: TicketCreate, db: Session = Depends(get_db), user: User = Depends(require_capture)):
    values, complete, now = capture_values(body, db)
    owner_id = user.id
    if body.created_for_user_id is not None:
        target = db.get(User, body.created_for_user_id)
        if target is None or not target.is_active:
            raise HTTPException(422, 'Target team member is missing or inactive')
        role = user.role.name if user.role else None
        if role != 'Admin' and (user.team_id is None or target.team_id != user.team_id):
            raise HTTPException(403, 'You may create a case only for a member of your own team')
        owner_id = target.id
    values.pop('created_for_user_id', None)
    values.update(created_by_id=user.id, owner_id=owner_id)
    if values.get("current_tier") is None:
        owner = db.get(User, owner_id)
        values["current_tier"] = owner.default_tier if owner else 2
    try:
        values['ticket_no'] = next_ticket_number(db, now) if complete else None
        ticket = Ticket(**values)
        db.add(ticket)
        db.flush()
        from app.services.routing import initialize_interval
        initialize_interval(db, ticket, now)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Case data changed; reload and try again') from None
    db.refresh(ticket)
    return ticket


@router.post('/tickets/{ticket_id}/follow-up', response_model=TicketOut, status_code=201)
def create_follow_up(ticket_id: int, body: TicketFollowUp, db: Session = Depends(get_db),
                     user: User = Depends(require_capture)):
    """CAP-09: create a linked follow-up while preserving the source case unchanged."""
    source = db.get(Ticket, ticket_id)
    if source is None:
        raise HTTPException(404, 'Source case not found')
    if source.status in ('DRAFT', 'DUPLICATE', 'CANCELLED'):
        raise HTTPException(409, 'A follow-up requires a published, non-cancelled case')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    values = {
        field: getattr(source, field) for field in (
            'ticket_type_id', 'organization_id', 'contact_id', 'department_id',
            'course_or_exam_id', 'product_instance_id', 'module_id', 'environment',
            'browser_device', 'source_url', 'exam_or_course_context', 'category_id',
            'symptom_id', 'service_stage_id', 'severity', 'impact_scope',
            'severity_overridden_reason', 'current_tier', 'sla_policy_id', 'is_exam_window'
        )
    }
    values.update(subject=body.subject or source.subject,
                  description=body.description if body.description is not None else source.description,
                  channel=body.channel or source.channel, status='NEW',
                  reported_at=now, created_at=now, created_by_id=user.id, owner_id=user.id,
                  assignee_id=None, master_ticket_id=source.id, ticket_no=next_ticket_number(db, now))
    try:
        ticket = Ticket(**values)
        db.add(ticket)
        db.flush()
        from app.services.routing import initialize_interval
        initialize_interval(db, ticket, now)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Unable to create follow-up; reload and try again') from None
    db.refresh(ticket)
    return ticket


def editable_ticket(db, ticket_id, user, draft_only=False):
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None:
        raise HTTPException(404, 'Ticket not found')
    if draft_only:
        if ticket.created_by_id != user.id:
            raise HTTPException(403, 'Only the creator can edit this draft')
        if ticket.status != 'DRAFT':
            raise HTTPException(409, 'Only DRAFT tickets support inline edits')
    else:
        role = user.role.name if user.role else None
        if role != 'Admin' and user.id not in (ticket.created_by_id, ticket.owner_id, ticket.assignee_id):
            raise HTTPException(403, 'Only the case creator, owner or assignee can edit its reported time')
    return ticket


def commit_edit(db, ticket):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Case data changed; reload and try again') from None
    db.refresh(ticket)
    return ticket


@router.patch('/tickets/{ticket_id}/draft-field', response_model=TicketOut)
def edit_draft_field(ticket_id: int, body: DraftFieldUpdate, db: Session = Depends(get_db),
                     user: User = Depends(require_capture)):
    ticket = editable_ticket(db, ticket_id, user, draft_only=True)

    data = {
    field: getattr(ticket, field)
    for field in TicketCreate.model_fields
    if field not in ('save_as_draft', 'created_for_user_id')
}
    data['reported_at'] = ticket.reported_at.replace(tzinfo=timezone.utc)
    data['save_as_draft'] = True
    data[body.field] = body.value

    # A parent selection changes the meaning of dependent IDs; never retain stale context.
    if body.field == 'organization_id' and body.value != ticket.organization_id:
        for field in ('contact_id', 'department_id', 'course_or_exam_id', 'product_instance_id',
                      'module_id', 'category_id', 'symptom_id', 'service_stage_id'):
            data[field] = None
    elif body.field == 'product_instance_id' and body.value != ticket.product_instance_id:
        for field in ('module_id', 'category_id', 'symptom_id', 'service_stage_id'):
            data[field] = None
    elif body.field == 'module_id' and body.value != ticket.module_id:
        data['category_id'] = None
    from pydantic import ValidationError
    try:
        selection = TicketCreate.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(422, [{'loc': error['loc'], 'msg': error['msg']} for error in exc.errors()]) from None
    values, _, _ = capture_values(selection, db, validate_reported=False)
    product_changed = data['product_instance_id'] != ticket.product_instance_id
    for field, value in values.items():
        if field not in ('created_at', 'reported_at', 'status') and (
            field != 'sla_policy_id' or product_changed
        ):
            setattr(ticket, field, value)
    return commit_edit(db, ticket)


@router.patch('/tickets/{ticket_id}/reported-at', response_model=TicketOut)
def edit_reported_time(ticket_id: int, body: ReportedTimeUpdate, db: Session = Depends(get_db),
                       user: User = Depends(require_capture)):
    ticket = editable_ticket(db, ticket_id, user)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reported = body.reported_at.astimezone(timezone.utc).replace(tzinfo=None)
    if reported > now or reported < now - timedelta(days=7):
        raise HTTPException(422, 'reported_at must be within the last 7 days')
    ticket.reported_at = reported
    ticket.is_exam_window = ticket.organization_id is not None and db.scalar(select(ExamWindow.id).where(
        ExamWindow.organization_id == ticket.organization_id, ExamWindow.is_active.is_(True),
        ExamWindow.starts_at <= reported, ExamWindow.ends_at > reported,
        or_(ExamWindow.department_id.is_(None), ExamWindow.department_id == ticket.department_id)
    ).limit(1)) is not None
    # The SLA engine is separate; do not invent or overwrite response/resolution clocks.
    return commit_edit(db, ticket)

@router.post('/tickets/{ticket_id}/resolve', response_model=TicketOut)
def resolve_ticket(
    ticket_id: int,
    body: TicketResolve,
    db: Session = Depends(get_db),
    user: User = Depends(require_capture),
):
    ticket = editable_ticket(db, ticket_id, user)
    from app.services.lifecycle import transition
    transition(db, ticket, body.model_dump() | {'status': 'RESOLVED'}, user)
    return commit_edit(db, ticket)


@router.patch('/tickets/{ticket_id}/status', response_model=TicketOut)
def update_ticket_status(ticket_id: int, payload: TicketStatusUpdatePayload,
                         db: Session = Depends(get_db), user: User = Depends(require_capture)):
    ticket = editable_ticket(db, ticket_id, user)
    from app.services.lifecycle import transition
    was_draft = ticket.status == "DRAFT"
    transition(db, ticket, payload.model_dump(exclude_unset=True), user)
    if was_draft and ticket.status == "NEW":
        ticket.ticket_no = next_ticket_number(db, datetime.now(timezone.utc).replace(tzinfo=None))
    return commit_edit(db, ticket)


@router.get('/tickets/queue-summary')
def queue_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = (now + timedelta(hours=7)).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=7)
    opened = Ticket.status.in_(OPEN_STATUSES)
    conditions = {
        'unassigned': and_(opened, Ticket.assignee_id.is_(None)),
        'mine': and_(opened, Ticket.assignee_id == user.id),
        'today': and_(Ticket.created_at >= today, Ticket.status.not_in(['DRAFT', 'DUPLICATE', 'CANCELLED'])),
        'drafts': and_(Ticket.status == 'DRAFT', Ticket.created_by_id == user.id),
    }
    result = db.execute(select(*(func.coalesce(func.sum(case((condition, 1), else_=0)), 0).label(name)
                                 for name, condition in conditions.items()))).mappings().one()
    return dict(result) | {'sla_at_risk': None}


@router.get('/tickets', response_model=list[TicketOut])
def tickets(organization_id: int | None = Query(None, ge=1), open_only: bool = False,
            mine: bool = False, unassigned: bool = False, drafts_only: bool = False, today_only: bool = False,
            q: str = Query('', max_length=255), ticket_status: str | None = None,
            offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Ticket)
    if organization_id is not None:
        get_record(db, Organization, organization_id)
        query = query.where(Ticket.organization_id == organization_id)
    if open_only:
        query = query.where(Ticket.status.in_(OPEN_STATUSES))
    if mine:
        query = query.where(Ticket.assignee_id == user.id)
    if unassigned:
        query = query.where(Ticket.assignee_id.is_(None))
    if drafts_only:
        query = query.where(Ticket.status == 'DRAFT', Ticket.created_by_id == user.id)
    if ticket_status is not None:
        if ticket_status not in TICKET_STATUSES:
            raise HTTPException(422, 'Unknown ticket status')
        query = query.where(Ticket.status == ticket_status)
    if today_only:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = (now + timedelta(hours=7)).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=7)
        query = query.where(Ticket.created_at >= today, Ticket.status.not_in(['DRAFT', 'DUPLICATE', 'CANCELLED']))
    if q.strip():
        query = query.where(or_(Ticket.subject.contains(q.strip(), autoescape=True),
                               Ticket.ticket_no.contains(q.strip(), autoescape=True)))
    ordering = (Ticket.created_at.asc(), Ticket.id.asc()) if drafts_only else (Ticket.created_at.desc(), Ticket.id.desc())
    return db.scalars(query.order_by(*ordering).offset(offset).limit(limit)).all()


@router.get('/tickets/{ticket_id}', response_model=TicketOut)
def ticket(ticket_id: int, db: Session = Depends(get_db)):
    return get_record(db, Ticket, ticket_id)


@router.get('/tickets/{ticket_id}/lifecycle-options')
def lifecycle_options(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(require_capture)):
    from app.services.lifecycle import authorize_case
    from app.core.state_machine import TRANSITION_RULES
    from app.db.models.master_data import ProblemType
    row = get_record(db, Ticket, ticket_id)
    authorize_case(row, user)
    role = user.role.name if user.role else None
    policy_role = 'Agent' if role in {'Specialist', 'Developer', 'Team Lead'} else role
    actions = [str(rule['to'].value) for rule in TRANSITION_RULES
               if rule['from'] == row.status and policy_role in rule['roles']]
    if row.status not in {'CLOSED', 'CANCELLED', 'DUPLICATE'}:
        actions += ['CANCELLED', 'DUPLICATE']
    def choices(model, *filters):
        return [{'id': record.id, 'name': getattr(record, 'name', None) or record.username}
                for record in db.scalars(select(model).where(*filters)).all()]
    return {'actions': actions,
        'assignees': choices(User, User.is_active.is_(True)),
        'causes': choices(CauseCode, CauseCode.is_active.is_(True)),
        'solutions': choices(SolutionCode, SolutionCode.is_active.is_(True)),
        'categories': choices(ProblemType, ProblemType.is_active.is_(True)),
        'instances': choices(ProductInstance, ProductInstance.organization_id == row.organization_id,
                             ProductInstance.is_active.is_(True))}

@router.post('/tickets/auto-close-resolved', status_code=200)
def auto_close_resolved_tickets(
    business_days: int = Query(3, ge=1, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(RoleChecker(['Admin']))
):
    """Trigger สำหรับรัน Auto-close Job (รองรับการกำหนดจำนวนวันทำการ)"""
    closed_count = run_auto_close_resolved_tickets(db, allowed_business_days=business_days)
    return {
        "message": f"Auto-close process completed successfully.",
        "closed_tickets_count": closed_count,
        "business_days_threshold": business_days
    }



# CAP-05: private, persistent attachment storage. Never expose this directory as StaticFiles.
ATTACHMENT_DIR = Path(os.getenv("ATTACHMENT_DIR", "/app/uploads/ticket-attachments"))
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "application/pdf": ".pdf"
    # "text/plain": ".txt", "image/gif": ".gif",
}

def _can_access_ticket(ticket, user):
    role = user.role.name if user.role else None
    return role == "Admin" or user.id in (ticket.created_by_id, ticket.owner_id, ticket.assignee_id)

def _attachment_json(row):
    return {"id": row.id, "ticket_id": row.ticket_id, "filename": row.original_name,
            "content_type": row.content_type, "size_bytes": row.size_bytes,
            "uploaded_by_id": row.uploaded_by_id, "created_at": row.created_at.isoformat(),
            "download_url": f"/api/v1/tickets/{row.ticket_id}/attachments/{row.id}/download"}

@router.get("/tickets/{ticket_id}/attachments")
def list_ticket_attachments(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = get_record(db, Ticket, ticket_id)
    if not _can_access_ticket(ticket, user):
        raise HTTPException(403, "You cannot access attachments for this case")
    rows = db.scalars(select(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id).order_by(TicketAttachment.created_at, TicketAttachment.id)).all()
    return [_attachment_json(row) for row in rows]

@router.post("/tickets/{ticket_id}/attachments", status_code=201)
async def upload_ticket_attachment(ticket_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_capture)):
    ticket = get_record(db, Ticket, ticket_id)
    if not _can_access_ticket(ticket, user):
        raise HTTPException(403, "Only the case creator, owner, assignee or Admin can attach files")
    content_type = (file.content_type or "application/octet-stream").lower().split(";")[0].strip()
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(415, "Only JPG, PNG, WEBP and PDF are supported")
    original_name = Path(file.filename or "attachment").name.replace("\\", "_")[:255] or "attachment"
    suffix = ALLOWED_ATTACHMENT_TYPES[content_type]
    stored_name = f"{uuid4().hex}{suffix}"
    ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
    target = ATTACHMENT_DIR / stored_name
    size = 0
    try:
        with target.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ATTACHMENT_BYTES:
                    raise HTTPException(413, "ไฟล์ต้องมีขนาดไม่เกิน 10 MB")
                output.write(chunk)
        if size == 0:
            raise HTTPException(422, "ไฟล์ว่างเปล่า")
        row = TicketAttachment(ticket_id=ticket_id, original_name=original_name, stored_name=stored_name,
                               content_type=content_type, size_bytes=size, uploaded_by_id=user.id)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _attachment_json(row)
    except Exception:
        target.unlink(missing_ok=True)
        db.rollback()
        raise
    finally:
        await file.close()

@router.get("/tickets/{ticket_id}/attachments/{attachment_id}/download")
def download_ticket_attachment(ticket_id: int, attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = get_record(db, Ticket, ticket_id)
    if not _can_access_ticket(ticket, user):
        raise HTTPException(403, "You cannot access attachments for this case")
    row = db.scalar(select(TicketAttachment).where(TicketAttachment.id == attachment_id, TicketAttachment.ticket_id == ticket_id))
    if row is None:
        raise HTTPException(404, "Attachment not found")
    target = ATTACHMENT_DIR / row.stored_name
    if not target.is_file():
        raise HTTPException(404, "Attachment file is missing from storage")
    return FileResponse(target, media_type=row.content_type, filename=row.original_name, content_disposition_type="inline" if row.content_type.startswith("image/") else "attachment")
