"""Minimal case capture; lifecycle transitions belong to the lifecycle tasks."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker, get_current_user
from app.api.v1.endpoints.customers import get_record
from app.api.v1.endpoints.product_configuration import CaseOptionsSelection, validate_selection
from app.db.models.customer import Contact, Organization
from app.db.models.customer_context import CourseOrExam, Department, ExamWindow
from app.db.models.master_data import Product, TicketType
from app.db.models.product import ProductInstance
from app.db.models.ticket import OPEN_STATUSES, TICKET_STATUSES, Ticket, TicketNumberSequence
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ticket import TicketCreate, TicketOut

router = APIRouter(dependencies=[Depends(get_current_user)])
require_capture = RoleChecker(['Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead'])


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


@router.post('/tickets', response_model=TicketOut, status_code=201)
def create_ticket(body: TicketCreate, db: Session = Depends(get_db), user: User = Depends(require_capture)):
    values = body.model_dump()
    values.pop('save_as_draft')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reported = body.reported_at.astimezone(timezone.utc).replace(tzinfo=None) if body.reported_at else now
    if reported > now or reported < now - timedelta(days=7):
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
                  created_by_id=user.id, owner_id=user.id, status='NEW' if complete else 'DRAFT',
                  sla_policy_id=policy_id, is_exam_window=exam)
    try:
        values['ticket_no'] = next_ticket_number(db, now) if complete else None
        ticket = Ticket(**values)
        db.add(ticket)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Case data changed; reload and try again') from None
    db.refresh(ticket)
    return ticket


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
