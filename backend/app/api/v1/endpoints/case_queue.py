"""Server-side work queue: filtering, SLA ordering and paging run in SQL.

The previous queue downloaded every case and filtered in the browser, then
requested each customer and product instance separately. This endpoint returns
one page with display names already resolved, so its cost depends on the page
size rather than on the number of cases (NFR-01).
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, not_, or_, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import get_current_user
from app.db.models.customer import Organization
from app.db.models.master_data import Product
from app.db.models.product import ProductInstance
from app.db.models.ticket import OPEN_STATUSES, TICKET_STATUSES, Ticket
from app.db.models.user import Team, User
from app.db.session import get_db
from app.services import sla_engine

router = APIRouter(tags=["Case queue"])
BANGKOK = ZoneInfo("Asia/Bangkok")
Scope = Literal["open", "all", "mine", "team", "unassigned", "today", "risk"]
SlaState = Literal["breached", "risk", "safe", "none"]
Sort = Literal["sla", "newest", "oldest"]


class QueueSla(BaseModel):
    remaining_seconds: int | None
    remaining_ratio: float | None
    paused: bool
    breached: bool
    due_at: datetime | None


class QueueRow(BaseModel):
    id: int
    ticket_no: str | None
    subject: str | None
    status: str
    severity: str | None
    channel: str | None
    current_tier: int | None
    created_at: datetime
    reported_at: datetime | None
    organization_id: int | None
    customer: str | None
    product_id: int | None
    product: str | None
    assignee_id: int | None
    assignee: str | None
    owner_id: int | None
    team: str | None = None
    sla: QueueSla | None


class QueuePage(BaseModel):
    items: list[QueueRow]
    total: int


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_midnight_utc(day: date):
    return datetime.combine(day, time(0), BANGKOK).astimezone(timezone.utc).replace(tzinfo=None)


def sla_condition(state: str, now: datetime):
    breached = or_(Ticket.sla_breached.is_(True), Ticket.sla_due_at <= now)
    return {
        "breached": breached,
        "risk": and_(not_(breached), Ticket.sla_risk_at <= now),
        "safe": and_(not_(breached), Ticket.sla_risk_at > now),
        "none": and_(Ticket.sla_breached.is_not(True), Ticket.sla_due_at.is_(None)),
    }[state]


@router.get("/case-queue", response_model=QueuePage)
def case_queue(
    scope: Scope = "open",
    product: str | None = Query(None, max_length=50, description="Product code, e.g. examplus"),
    status: list[str] = Query([]),
    severity: list[Literal["S1", "S2", "S3", "S4"]] = Query([]),
    tier: list[int] = Query([]),
    channel: list[str] = Query([]),
    sla: list[SlaState] = Query([]),
    assignee: Literal["any", "mine", "unassigned"] = "any",
    created_from: date | None = None,
    created_to: date | None = None,
    q: str = Query("", max_length=255),
    sort: Sort = "sla",
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = utcnow()
    assignee_user = aliased(User)
    query = (
        select(Ticket, Organization.name, Product.id, Product.name, assignee_user.full_name, assignee_user.username,
               Team.name)
        .outerjoin(Organization, Organization.id == Ticket.organization_id)
        .outerjoin(ProductInstance, ProductInstance.id == Ticket.product_instance_id)
        .outerjoin(Product, Product.id == ProductInstance.product_id)
        .outerjoin(assignee_user, assignee_user.id == Ticket.assignee_id)
        .outerjoin(Team, Team.id == Ticket.team_id)
        .where(Ticket.status != "DRAFT")  # drafts belong to their creator's draft list
    )
    statuses = [value for value in status if value in TICKET_STATUSES]
    if statuses:
        query = query.where(Ticket.status.in_(statuses))
    elif scope != "all":
        query = query.where(Ticket.status.in_(OPEN_STATUSES))
    if scope == "team":
        query = query.where(Ticket.team_id == user.team_id) if user.team_id else query.where(False)
    if scope == "mine" or assignee == "mine":
        query = query.where(Ticket.assignee_id == user.id)
    if scope == "unassigned" or assignee == "unassigned":
        query = query.where(Ticket.assignee_id.is_(None))
    if scope == "today":
        today = datetime.now(BANGKOK).date()
        query = query.where(Ticket.created_at >= local_midnight_utc(today))
    if scope == "risk":
        query = query.where(or_(sla_condition("risk", now), sla_condition("breached", now)))
    if product:
        query = query.where(func.lower(Product.code) == product.lower())
    if severity:
        query = query.where(Ticket.severity.in_(severity))
    if tier:
        query = query.where(Ticket.current_tier.in_(tier))
    if channel:
        query = query.where(Ticket.channel.in_(channel))
    if sla:
        query = query.where(or_(*(sla_condition(state, now) for state in sla)))
    if created_from:
        query = query.where(Ticket.created_at >= local_midnight_utc(created_from))
    if created_to:
        query = query.where(Ticket.created_at < local_midnight_utc(created_to + timedelta(days=1)))
    text = q.strip()
    if text:
        query = query.where(or_(Ticket.ticket_no.contains(text, autoescape=True),
                                Ticket.subject.contains(text, autoescape=True),
                                Organization.name.contains(text, autoescape=True)))

    total = db.scalar(select(func.count()).select_from(query.with_only_columns(Ticket.id).subquery()))
    ordering = {
        "sla": (case((Ticket.sla_due_at.is_(None), 1), else_=0), Ticket.sla_due_at.asc(),
                Ticket.created_at.desc()),
        "newest": (Ticket.created_at.desc(),),
        "oldest": (Ticket.created_at.asc(),),
    }[sort]
    rows = db.execute(query.order_by(*ordering, Ticket.id.desc()).offset(offset).limit(limit)).all()

    schedule = sla_engine.schedule_for(db)
    items = []
    for ticket, customer, product_id, product_name, full_name, username, team in rows:
        state = sla_engine.measurement(db, ticket, now, schedule)
        items.append(QueueRow(
            id=ticket.id, ticket_no=ticket.ticket_no, subject=ticket.subject, status=ticket.status,
            severity=ticket.severity, channel=ticket.channel, current_tier=ticket.current_tier,
            created_at=ticket.created_at, reported_at=ticket.reported_at,
            organization_id=ticket.organization_id, customer=customer, product_id=product_id,
            product=product_name, assignee_id=ticket.assignee_id, assignee=full_name or username,
            owner_id=ticket.owner_id, team=team,
            sla=QueueSla(remaining_seconds=state["remaining_seconds"], remaining_ratio=state["remaining_ratio"],
                         paused=state["paused"], breached=state["breached"], due_at=ticket.sla_due_at)
            if state else None,
        ))
    return QueuePage(items=items, total=total)
