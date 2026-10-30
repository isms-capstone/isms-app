"""ESC API: policy/configuration, audited mutations, workload and in-app alerts."""

from typing import Annotated

from app.api.deps import RoleChecker, get_current_user, require_admin
from app.db.models.master_data import BusinessCalendar, Product
from app.db.models.routing import (
    ProductTierRoute,
    RoutingJobLease,
    RoutingNotification,
    RoutingPolicy,
    TeamRouting,
)
from app.db.models.ticket import OPEN_STATUSES, Ticket
from app.db.models.user import Team, User
from app.db.session import get_db
from app.schemas.routing import (
    AssignInput,
    AvailabilityInput,
    BulkInput,
    HandoffInput,
    LeaderInput,
    PolicyInput,
    ReturnInput,
    RouteInput,
    UserTierInput,
    Versioned,
)
from app.services import routing as service
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

router = APIRouter(dependencies=[Depends(get_current_user)])
support = RoleChecker(sorted(service.SUPPORT_ROLES))
Database = Annotated[Session, Depends(get_db)]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
SupportUser = Annotated[User, Depends(support)]


def commit(db):
    try:
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(
            409, "Routing data changed concurrently; refresh and retry"
        ) from None


def existing(db, model, record_id):
    row = db.get(model, record_id)
    if row is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return row


def member(row):
    return {
        "id": row.id,
        "name": row.full_name or row.username,
        "team_id": row.team_id,
        "default_tier": row.default_tier,
        "is_available": row.is_available,
        "is_active": row.is_active,
        "role": service.role(row),
    }


@router.get("/routing/options")
def options(db: Database, user: SupportUser):
    return {
        "users": [
            member(row)
            for row in db.scalars(select(User).order_by(User.id)).all()
            if service.role(row) in service.SUPPORT_ROLES
        ],
        "teams": [
            {"id": row.id, "name": row.name}
            for row in db.scalars(select(Team).order_by(Team.id)).all()
        ],
        "products": [
            {"id": row.id, "name": row.name}
            for row in db.scalars(
                select(Product).where(Product.is_active.is_(True))
            ).all()
        ],
        "calendars": [
            {"id": row.id, "name": row.name}
            for row in db.scalars(
                select(BusinessCalendar).where(BusinessCalendar.is_active.is_(True))
            ).all()
        ],
        "routes": [
            {"product_id": row.product_id, "tier": row.tier, "team_id": row.team_id}
            for row in db.scalars(select(ProductTierRoute)).all()
        ],
    }


@router.get("/routing/config", dependencies=[Depends(require_admin)])
def config(db: Database):
    policy = db.get(RoutingPolicy, 1)
    worker = db.get(RoutingJobLease, 1)
    return {
        "worker": {"last_success_at": worker.last_success_at} if worker else None,
        "policy": {
            "s1_minutes": policy.s1_minutes if policy else 15,
            "enabled": policy.enabled if policy else True,
            "business_calendar_id": policy.business_calendar_id if policy else None,
        },
        "leaders": [
            {"team_id": row.team_id, "leader_id": row.leader_id}
            for row in db.scalars(select(TeamRouting)).all()
        ],
    }


@router.put("/routing/routes", dependencies=[Depends(require_admin)])
def set_route(body: RouteInput, db: Database):
    product = existing(db, Product, body.product_id)
    if not product.is_active:
        raise HTTPException(422, "Product is inactive")
    existing(db, Team, body.team_id)
    route = db.scalar(
        select(ProductTierRoute).where(
            ProductTierRoute.product_id == body.product_id,
            ProductTierRoute.tier == body.tier,
        )
    )
    if route:
        route.team_id = body.team_id
    else:
        db.add(ProductTierRoute(**body.model_dump()))
    commit(db)
    return body.model_dump()


@router.put("/routing/teams/{team_id}/leader", dependencies=[Depends(require_admin)])
def set_leader(team_id: int, body: LeaderInput, db: Database):
    existing(db, Team, team_id)
    leader = existing(db, User, body.leader_id)
    if (
        not leader.is_active
        or leader.team_id != team_id
        or service.role(leader) not in service.SUPPORT_ROLES
    ):
        raise HTTPException(422, "Leader must be an active support member of that team")
    config = db.get(TeamRouting, team_id)
    if config:
        config.leader_id = leader.id
    else:
        db.add(TeamRouting(team_id=team_id, leader_id=leader.id))
    commit(db)
    return {"team_id": team_id, "leader_id": leader.id}


@router.put("/routing/users/{user_id}/tier", dependencies=[Depends(require_admin)])
def set_tier(user_id: int, body: UserTierInput, db: Database):
    row = existing(db, User, user_id)
    row.default_tier = body.default_tier
    commit(db)
    return member(row)


@router.put("/routing/policy", dependencies=[Depends(require_admin)])
def set_policy(body: PolicyInput, db: Database):
    if body.business_calendar_id:
        calendar = existing(db, BusinessCalendar, body.business_calendar_id)
        if not calendar.is_active:
            raise HTTPException(422, "Business calendar is inactive")
    policy = db.get(RoutingPolicy, 1)
    if policy is None:
        policy = RoutingPolicy(id=1)
        db.add(policy)
    for name, value in body.model_dump().items():
        setattr(policy, name, value)
    commit(db)
    return body.model_dump()


@router.get("/routing/me")
def workload(db: Database, user: SupportUser):
    return member(user) | {
        "tickets": [
            {
                "id": row.id,
                "ticket_no": row.ticket_no,
                "subject": row.subject,
                "tier": row.current_tier,
            }
            for row in db.scalars(
                select(Ticket)
                .where(Ticket.assignee_id == user.id, Ticket.status.in_(OPEN_STATUSES))
                .order_by(Ticket.id)
            ).all()
        ]
    }


@router.put("/routing/me/availability")
def availability(
    body: AvailabilityInput,
    db: Database,
    user: SupportUser,
):
    row = existing(db, User, user.id)
    row.is_available = body.is_available
    commit(db)
    return member(row)


@router.post("/routing/me/handover")
def bulk(body: BulkInput, db: Database, user: SupportUser):
    ids = service.bulk_handover(db, body, user)
    commit(db)
    return {"ticket_ids": ids, "count": len(ids)}


def routing_state(db, ticket, user):
    state = service.summary(db, ticket)
    authorized = False
    try:
        service.authorize(db, ticket, user)
        authorized = True
    except HTTPException:
        pass
    eligible = []
    for candidate in db.scalars(
        select(User).where(User.is_active.is_(True), User.is_available.is_(True))
    ).all():
        team_id = service.route_team(db, ticket, candidate.default_tier)
        if (
            team_id is not None
            and service.role(candidate) in service.SUPPORT_ROLES
            and candidate.team_id == team_id
        ):
            eligible.append(member(candidate))
    active = ticket.status in OPEN_STATUSES
    latest = next(
        (
            row
            for row in reversed(state["events"])
            if row["kind"] in {"handoff", "auto_escalate", "return"}
        ),
        None,
    )
    destination = user.id == ticket.assignee_id or service.lead_for(
        db, user, service.route_team(db, ticket)
    )
    state.update(
        eligible_users=eligible,
        permissions={
            "handoff": active
            and authorized
            and ticket.current_tier is not None
            and ticket.current_tier > 0,
            "return_case": active
            and authorized
            and destination
            and bool(latest and latest["kind"] in {"handoff", "auto_escalate"}),
            "assign": active
            and service.lead_for(db, user, service.route_team(db, ticket)),
            "self_assign": active
            and ticket.status == "NEW"
            and ticket.assignee_id is None
            and any(
                row["id"] == user.id and row["default_tier"] == ticket.current_tier
                for row in eligible
            ),
            "respond": active and authorized and ticket.first_response_at is None,
        },
        return_event_id=latest["id"]
        if latest and latest["kind"] in {"handoff", "auto_escalate"}
        else None,
    )
    return state


@router.get("/tickets/{ticket_id}/routing")
def state(
    ticket_id: int,
    db: Database,
    user: AuthenticatedUser,
):
    return routing_state(db, existing(db, Ticket, ticket_id), user)


@router.post("/tickets/{ticket_id}/handoff")
def handoff(
    ticket_id: int,
    body: HandoffInput,
    db: Database,
    user: SupportUser,
):
    ticket = service.handoff(db, ticket_id, body, user)
    commit(db)
    return routing_state(db, ticket, user)


@router.post("/tickets/{ticket_id}/return")
def return_case(
    ticket_id: int,
    body: ReturnInput,
    db: Database,
    user: SupportUser,
):
    ticket = service.return_case(db, ticket_id, body, user)
    commit(db)
    return routing_state(db, ticket, user)


@router.post("/tickets/{ticket_id}/assign")
def assign(
    ticket_id: int,
    body: AssignInput,
    db: Database,
    user: SupportUser,
):
    ticket = service.assign(db, ticket_id, body, user)
    commit(db)
    return routing_state(db, ticket, user)


@router.post("/tickets/{ticket_id}/self-assign")
def self_assign(
    ticket_id: int,
    body: Versioned,
    db: Database,
    user: SupportUser,
):
    ticket = service.assign(db, ticket_id, body, user, self_assign=True)
    commit(db)
    return routing_state(db, ticket, user)


@router.post("/tickets/{ticket_id}/respond")
def respond(
    ticket_id: int,
    body: Versioned,
    db: Database,
    user: SupportUser,
):
    ticket = service.lock_case(db, ticket_id, body.expected_version)
    service.authorize(db, ticket, user)
    if ticket.first_response_at is not None:
        raise HTTPException(409, "Response was already recorded")
    service.claim_version(db, ticket, body.expected_version)
    ticket.first_response_at = service.utcnow()
    service.record(
        db,
        ticket,
        db.get(User, ticket.assignee_id) if ticket.assignee_id else None,
        ticket.current_tier,
        user,
        "response",
        "Operator acknowledged the case",
    )
    commit(db)
    return routing_state(db, ticket, user)


@router.get("/routing/notifications")
def notifications(db: Database, user: AuthenticatedUser):
    rows = db.scalars(
        select(RoutingNotification)
        .where(RoutingNotification.recipient_id == user.id)
        .order_by(RoutingNotification.id.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": row.id,
            "ticket_id": row.ticket_id,
            "kind": row.kind,
            "message": row.message,
            "created_at": row.created_at,
            "read_at": row.read_at,
        }
        for row in rows
    ]


@router.post("/routing/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    db: Database,
    user: AuthenticatedUser,
):
    row = db.scalar(
        select(RoutingNotification).where(
            RoutingNotification.id == notification_id,
            RoutingNotification.recipient_id == user.id,
        )
    )
    if row is None:
        raise HTTPException(404, "Notification not found")
    row.read_at = row.read_at or service.utcnow()
    commit(db)
    return {"id": row.id, "read_at": row.read_at}
