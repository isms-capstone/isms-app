"""Search and export use the same case visibility and filter rules."""
import csv
import io
from datetime import timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker
from app.db.models.case_search import CaseExportAudit, CaseSearchToken, CaseSearchView
from app.db.models.customer import Organization
from app.db.models.master_data import Product
from app.db.models.product import ProductInstance
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.user import User
from app.db.models.work_category import TicketWorklog
from app.db.session import get_db
from app.schemas.ticket import TicketOut
from app.services.case_search_index import search_tokens


router = APIRouter(prefix='/case-search')
search_user = RoleChecker(['Admin', 'Agent', 'Specialist', 'Developer', 'Team Lead', 'Executive'])
export_user = RoleChecker(['Admin', 'Team Lead', 'Executive'])
MAX_EXPORT = 10000


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')

    q: str = Field('', max_length=255)
    status: TicketStatus | None = None
    organization_id: int | None = Field(None, ge=1)
    product_id: int | None = Field(None, ge=1)
    assignee_id: int | None = Field(None, ge=1)
    reported_from: AwareDatetime | None = None
    reported_before: AwareDatetime | None = None
    severity: Literal['S1', 'S2', 'S3', 'S4'] | None = None

    @model_validator(mode='after')
    def validate_period(self):
        if self.reported_from and self.reported_before and self.reported_from >= self.reported_before:
            raise ValueError('Start must be earlier than end')
        return self


class SavedViewInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=1, max_length=100)
    scope: Literal['personal', 'team']
    filters: SearchFilters

    @field_validator('name', mode='before')
    @classmethod
    def trim(cls, name):
        return name.strip() if isinstance(name, str) else name


def visible_cases(user):
    query = select(Ticket).where(or_(Ticket.status != 'DRAFT', Ticket.created_by_id == user.id))
    if user.role.name in {'Admin', 'Executive'}:
        return query
    participants = [user.id]
    if getattr(user, 'team_id', None):
        participants = select(User.id).where(User.team_id == user.team_id)
    return query.where(or_(*(field.in_(participants) for field in (
        Ticket.created_by_id, Ticket.owner_id, Ticket.assignee_id))))


def matching_cases(filters, user):
    query = visible_cases(user)
    for name in ('status', 'organization_id', 'assignee_id', 'severity'):
        value = getattr(filters, name)
        if value is not None:
            query = query.where(getattr(Ticket, name) == value)
    if filters.product_id:
        query = query.where(Ticket.product_instance_id.in_(
            select(ProductInstance.id).where(ProductInstance.product_id == filters.product_id)))
    if filters.reported_from:
        query = query.where(Ticket.reported_at >= filters.reported_from.astimezone(timezone.utc).replace(tzinfo=None))
    if filters.reported_before:
        query = query.where(Ticket.reported_at < filters.reported_before.astimezone(timezone.utc).replace(tzinfo=None))
    if filters.q.strip():
        text = filters.q.strip()
        terms = search_tokens(filters.q)
        # Thai word segmentation is not stable across contexts (e.g. "ขอส่งออกข้อสอบ"
        # splits as "ส่ง" + "ออกข้อสอบ"), so a plain substring match on the case
        # text and work log complements the token index (SEA-01).
        matches = [
            Ticket.ticket_no.contains(text, autoescape=True),
            Ticket.subject.contains(text, autoescape=True),
            Ticket.description.contains(text, autoescape=True),
            Ticket.id.in_(select(TicketWorklog.ticket_id)
                          .where(TicketWorklog.message.contains(text, autoescape=True))),
        ]
        if terms:
            matches.append(Ticket.id.in_(
                select(CaseSearchToken.ticket_id)
                .where(CaseSearchToken.token.in_(terms))
                .group_by(CaseSearchToken.ticket_id)
                .having(func.count(func.distinct(CaseSearchToken.token)) == len(terms))
            ))
        query = query.where(or_(*matches))
    return query


@router.post('/query')
def query_cases(filters: SearchFilters, db: Session = Depends(get_db), user=Depends(search_user),
                offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    query = matching_cases(filters, user)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Ticket.reported_at.desc(), Ticket.id.desc()).offset(offset).limit(limit))
    return {'items': [TicketOut.model_validate(row) for row in items], 'total': total}


@router.get('/options')
def search_options(db: Session = Depends(get_db), user=Depends(search_user)):
    scope = visible_cases(user)
    organizations = db.execute(select(Organization.id, Organization.name).where(
        Organization.id.in_(scope.with_only_columns(Ticket.organization_id))).order_by(Organization.name))
    products = db.execute(select(Product.id, Product.name).where(Product.id.in_(
        select(ProductInstance.product_id).where(
            ProductInstance.id.in_(scope.with_only_columns(Ticket.product_instance_id))))).order_by(Product.name))
    assignees = db.execute(select(User.id, func.coalesce(User.full_name, User.username)).where(
        User.id.in_(scope.with_only_columns(Ticket.assignee_id))).order_by(User.username))

    def options(rows):
        return [{'id': row_id, 'name': name} for row_id, name in rows]

    return {'organizations': options(organizations), 'products': options(products),
            'assignees': options(assignees), 'statuses': list(TicketStatus),
            'can_share': bool(getattr(user, 'team_id', None)), 'can_export': user.role.name in export_user.allowed_roles}


def view_json(row):
    return {'id': row.id, 'name': row.name, 'scope': 'team' if row.team_id else 'personal',
            'filters': row.filters}


@router.get('/views')
def list_views(db: Session = Depends(get_db), user=Depends(search_user)):
    visible = (CaseSearchView.owner_id == user.id) & CaseSearchView.team_id.is_(None)
    if getattr(user, 'team_id', None):
        visible = or_(visible, CaseSearchView.team_id == user.team_id)
    rows = db.scalars(select(CaseSearchView).where(visible).order_by(CaseSearchView.name, CaseSearchView.id))
    return [view_json(row) for row in rows]


@router.post('/views', status_code=201)
def save_view(body: SavedViewInput, db: Session = Depends(get_db), user=Depends(search_user)):
    team = getattr(user, 'team_id', None) if body.scope == 'team' else None
    if body.scope == 'team' and not team:
        raise HTTPException(403, 'บัญชีนี้ยังไม่อยู่ในทีม กรุณาติดต่อผู้ดูแลระบบ')
    row = CaseSearchView(name=body.name, owner_id=user.id, team_id=team,
                         filters=body.filters.model_dump(mode='json'))
    db.add(row)
    db.commit()
    db.refresh(row)
    return view_json(row)


def spreadsheet_text(value):
    if not isinstance(value, str):
        return value
    cleaned = ILLEGAL_CHARACTERS_RE.sub('', value)
    if cleaned.startswith(('\t', '\r', '\n')) or cleaned.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + cleaned
    return cleaned


@router.post('/export/{file_format}')
def export_cases(file_format: Literal['csv', 'xlsx'], filters: SearchFilters,
                 db: Session = Depends(get_db), user=Depends(export_user)):
    query = matching_cases(filters, user).order_by(Ticket.reported_at.desc(), Ticket.id.desc())
    tickets = list(db.scalars(query.limit(MAX_EXPORT + 1)))
    if len(tickets) > MAX_EXPORT:
        raise HTTPException(422, 'ผลลัพธ์เกิน 10,000 เคส กรุณาเพิ่มตัวกรองก่อนส่งออก')
    fields = ('ticket_no', 'subject', 'status', 'severity', 'organization_id', 'assignee_id', 'reported_at')
    rows = [fields]
    for ticket in tickets:
        rows.append(tuple(spreadsheet_text(getattr(ticket, field)) for field in fields))
    if file_format == 'csv':
        stream = io.StringIO()
        csv.writer(stream).writerows(rows)
        content = stream.getvalue().encode('utf-8-sig')
        mime = 'text/csv'
    else:
        stream = io.BytesIO()
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet('Cases')
        for row in rows:
            sheet.append(row)
        workbook.save(stream)
        content = stream.getvalue()
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    db.add(CaseExportAudit(actor_id=user.id, format=file_format,
                           filters=filters.model_dump(mode='json'), ticket_ids=[ticket.id for ticket in tickets]))
    db.commit()
    return Response(content, media_type=mime, headers={
        'Content-Disposition': f'attachment; filename="cases.{file_format}"',
        'Cache-Control': 'private, no-store',
    })
