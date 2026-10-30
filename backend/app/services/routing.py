"""ESC operations. Caller owns the transaction; every mutation uses an optimistic version."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, update

from app.db.models.master_data import Product
from app.db.models.product import ProductInstance
from app.db.models.routing import (
    ProductTierRoute,
    RoutingEvent,
    RoutingNotification,
    TeamRouting,
    TierInterval,
)
from app.db.models.ticket import OPEN_STATUSES, Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import Role, User

SUPPORT_ROLES = {"Admin", "Team Lead", "Agent", "Specialist", "Developer"}
TERMINAL = {"DRAFT", "RESOLVED", "CLOSED", "CANCELLED", "DUPLICATE"}


def utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


def role(user):
    return user.role.name if user.role else None


def product_id(db, ticket):
    instance = (
        db.get(ProductInstance, ticket.product_instance_id)
        if ticket.product_instance_id
        else None
    )
    return instance.product_id if instance else None


def route_team(db, ticket, tier=None):
    tier = ticket.current_tier if tier is None else tier
    product = product_id(db, ticket)
    route = (
        db.scalar(
            select(ProductTierRoute).where(
                ProductTierRoute.product_id == product, ProductTierRoute.tier == tier
            )
        )
        if product
        else None
    )
    if route:
        return route.team_id
    if tier == 2:
        from app.services.automation_rules import apply_automation_rules

        values = {
            name: getattr(ticket, name, None)
            for name in (
                "severity",
                "status",
                "channel",
                "module_id",
                "symptom_id",
                "service_stage_id",
                "ticket_type_id",
            )
        }
        values.update(product_id=product, problem_type_id=ticket.category_id)
        automated = apply_automation_rules(db, values)
        if automated.get("team_id"):
            return automated["team_id"]
    if product and tier == 2:
        catalogue = db.get(Product, product)
        if catalogue.default_team_id:
            return catalogue.default_team_id
    if tier == ticket.current_tier:
        member = db.get(User, ticket.assignee_id or ticket.owner_id)
        return member.team_id if member else None
    return None


def lead_for(db, user, team_id):
    if role(user) == "Admin":
        return True
    if not team_id:
        return False
    lead = db.get(TeamRouting, team_id)
    return (role(user) == "Team Lead" and user.team_id == team_id) or bool(
        lead and lead.leader_id == user.id
    )


def authorize(db, ticket, user):
    if role(user) not in SUPPORT_ROLES:
        raise HTTPException(403, "Support role required")
    if user.id in (
        ticket.owner_id,
        ticket.assignee_id,
        ticket.created_by_id,
    ) or lead_for(db, user, route_team(db, ticket)):
        return
    raise HTTPException(
        403, "Only case participants or the responsible team lead may route this case"
    )


def target_user(db, ticket, user_id, tier):
    target = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        not target
        or not target.is_active
        or not target.is_available
        or role(target) not in SUPPORT_ROLES
    ):
        raise HTTPException(
            422, "Recipient must be active, available and have a support role"
        )
    if target.default_tier != tier:
        raise HTTPException(
            422, "Recipient default tier does not match the destination tier"
        )
    team = route_team(db, ticket, tier)
    if team is None or target.team_id != team:
        raise HTTPException(
            422,
            "Configure a destination product/tier team and select a member of that team",
        )
    return target


def lock_case(db, ticket_id, expected_version=None):
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None:
        raise HTTPException(404, "Case not found")
    if ticket.status in TERMINAL:
        raise HTTPException(409, "Routing requires an active published case")
    if expected_version is not None and ticket.routing_version != expected_version:
        raise HTTPException(409, "Case routing changed; refresh before retrying")
    return ticket


def claim_version(db, ticket, expected):
    result = db.execute(
        update(Ticket)
        .where(Ticket.id == ticket.id, Ticket.routing_version == expected)
        .values(routing_version=expected + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise HTTPException(409, "Case was changed by another operator")
    ticket.routing_version = expected + 1


def initialize_interval(db, ticket, now=None, history_id=None):
    if ticket.status not in OPEN_STATUSES:
        return
    current = db.scalar(
        select(TierInterval).where(TierInterval.open_ticket_id == ticket.id)
    )
    if current is None:
        if history_id is None:
            history = TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=ticket.status,
                to_status=ticket.status,
                actor_id=ticket.created_by_id,
                created_at=now or ticket.created_at,
                details={"operation": "tier_entry", "tier": ticket.current_tier},
            )
            db.add(history)
            db.flush()
            history_id = history.id
        db.add(
            TierInterval(
                ticket_id=ticket.id,
                open_ticket_id=ticket.id,
                tier=ticket.current_tier if ticket.current_tier is not None else 2,
                entered_at=now or ticket.created_at,
                status_history_id=history_id,
                is_estimated=False,
            )
        )
        db.flush()


def close_interval(db, ticket, now):
    for interval in db.scalars(
        select(TierInterval).where(TierInterval.open_ticket_id == ticket.id)
    ).all():
        interval.exited_at = now
        interval.open_ticket_id = None
    db.flush()


def record(
    db,
    ticket,
    target,
    tier,
    actor,
    kind,
    reason,
    checked=None,
    requested=None,
    return_of_id=None,
    now=None,
):
    now = now or utcnow()
    old_tier = ticket.current_tier if ticket.current_tier is not None else 2
    history = TicketStatusHistory(
        ticket_id=ticket.id,
        from_status=ticket.status,
        to_status=ticket.status,
        actor_id=actor.id if actor else None,
        created_at=now,
        details={
            "operation": kind,
            "reason": reason,
            "checked": checked,
            "requested": requested,
        },
    )
    db.add(history)
    db.flush()
    event = RoutingEvent(
        ticket_id=ticket.id,
        status_history_id=history.id,
        actor_id=actor.id if actor else None,
        kind=kind,
        from_user_id=ticket.assignee_id,
        to_user_id=target.id if target else None,
        from_tier=old_tier,
        to_tier=tier,
        reason=reason,
        checked=checked,
        requested=requested,
        return_of_id=return_of_id,
        created_at=now,
    )
    db.add(event)
    initialize_interval(db, ticket, now, history.id)
    if old_tier != tier:
        close_interval(db, ticket, now)
    ticket.assignee_id = target.id if target else None
    ticket.current_tier = tier
    if old_tier != tier:
        initialize_interval(db, ticket, now, history.id)
    db.flush()
    # owner_id, ticket_no, status and created_at deliberately stay unchanged.
    return event


def handoff(db, ticket_id, body, user):
    ticket = lock_case(db, ticket_id, body.expected_version)
    authorize(db, ticket, user)
    if body.tier >= (ticket.current_tier if ticket.current_tier is not None else 2):
        raise HTTPException(
            422,
            "Handoff must escalate from Tier 2 to 1, or from 1 to 0; use assignment within a tier",
        )
    target = target_user(db, ticket, body.assignee_id, body.tier)
    claim_version(db, ticket, body.expected_version)
    record(
        db,
        ticket,
        target,
        body.tier,
        user,
        "handoff",
        body.reason,
        body.checked,
        body.requested,
    )
    return ticket


def return_case(db, ticket_id, body, user):
    ticket = lock_case(db, ticket_id, body.expected_version)
    authorize(db, ticket, user)
    original = db.get(RoutingEvent, body.event_id)
    latest = db.scalar(
        select(RoutingEvent)
        .where(
            RoutingEvent.ticket_id == ticket.id,
            RoutingEvent.kind.in_(["handoff", "auto_escalate", "return"]),
        )
        .order_by(RoutingEvent.id.desc())
        .limit(1)
    )
    if (
        not original
        or original.ticket_id != ticket.id
        or (not latest or original.id != latest.id)
        or original.kind not in {"handoff", "auto_escalate"}
    ):
        raise HTTPException(409, "Only the current unreturned handoff can be returned")
    if user.id != ticket.assignee_id and not lead_for(db, user, route_team(db, ticket)):
        raise HTTPException(
            403, "Only the destination assignee or team lead can return a case"
        )
    if db.scalar(
        select(RoutingEvent.id).where(RoutingEvent.return_of_id == original.id)
    ):
        raise HTTPException(409, "This handoff was already returned")
    target_id = original.from_user_id or ticket.owner_id
    target = target_user(db, ticket, target_id, original.from_tier)
    claim_version(db, ticket, body.expected_version)
    record(
        db,
        ticket,
        target,
        original.from_tier,
        user,
        "return",
        body.reason,
        return_of_id=original.id,
    )
    return ticket


def assign(db, ticket_id, body, user, self_assign=False):
    ticket = lock_case(db, ticket_id, body.expected_version)
    if self_assign:
        if ticket.status != "NEW" or ticket.assignee_id is not None:
            raise HTTPException(409, "Self-assignment requires an unassigned NEW case")
        target = target_user(db, ticket, user.id, ticket.current_tier)
    else:
        if not lead_for(db, user, route_team(db, ticket)):
            raise HTTPException(
                403, "Manual assignment requires the responsible team lead or Admin"
            )
        target = target_user(db, ticket, body.assignee_id, ticket.current_tier)
    claim_version(db, ticket, body.expected_version)
    record(
        db,
        ticket,
        target,
        ticket.current_tier,
        user,
        "self_assign" if self_assign else "assign",
        "Picked from the queue" if self_assign else body.reason,
    )
    return ticket


def bulk_handover(db, body, user):
    if role(user) not in SUPPORT_ROLES:
        raise HTTPException(403, "Support role required")
    tickets = db.scalars(
        select(Ticket)
        .where(Ticket.assignee_id == user.id, Ticket.status.in_(OPEN_STATUSES))
        .order_by(Ticket.id)
        .with_for_update()
    ).all()
    if len(set(body.ticket_ids)) != len(body.ticket_ids) or set(body.ticket_ids) != {
        ticket.id for ticket in tickets
    }:
        raise HTTPException(
            409,
            "The active workload changed; refresh and hand over the entire current list",
        )
    if body.assignee_id == user.id:
        raise HTTPException(422, "Select another recipient")
    targets = [
        target_user(db, ticket, body.assignee_id, ticket.current_tier)
        for ticket in tickets
    ]
    for ticket, target in zip(tickets, targets):
        claim_version(db, ticket, ticket.routing_version)
        record(
            db, ticket, target, ticket.current_tier, user, "bulk_handover", body.reason
        )
    return [ticket.id for ticket in tickets]


def notify(db, ticket, recipients, kind, key, message, now):
    added = 0
    for recipient in recipients:
        dedupe = f"{key}:{recipient.id}"
        if not db.scalar(
            select(RoutingNotification.id).where(
                RoutingNotification.dedupe_key == dedupe
            )
        ):
            db.add(
                RoutingNotification(
                    recipient_id=recipient.id,
                    ticket_id=ticket.id,
                    kind=kind,
                    dedupe_key=dedupe,
                    message=message,
                    created_at=now,
                )
            )
            added += 1
    return added


def leaders(db, ticket):
    team_id = route_team(db, ticket)
    config = db.get(TeamRouting, team_id) if team_id else None
    if config:
        leader = db.get(User, config.leader_id)
        if leader and leader.is_active:
            return [leader]
    if team_id:
        heads = db.scalars(
            select(User)
            .join(Role)
            .where(
                Role.name == "Team Lead",
                User.team_id == team_id,
                User.is_active.is_(True),
            )
        ).all()
        if heads:
            return heads
    # Misconfigured routes remain visible to administrators, never silently disappear.
    return db.scalars(
        select(User).join(Role).where(Role.name == "Admin", User.is_active.is_(True))
    ).all()


def summary(db, ticket, now=None):
    now = now or utcnow()

    def person(user_id):
        user = db.get(User, user_id) if user_id else None
        return (
            {"id": user.id, "name": user.full_name or user.username} if user else None
        )

    events = db.scalars(
        select(RoutingEvent)
        .where(RoutingEvent.ticket_id == ticket.id)
        .order_by(RoutingEvent.id)
    ).all()
    intervals = db.scalars(
        select(TierInterval)
        .where(TierInterval.ticket_id == ticket.id)
        .order_by(TierInterval.id)
    ).all()
    totals = {str(tier): 0 for tier in (2, 1, 0)}
    for interval in intervals:
        totals[str(interval.tier)] += max(
            0, int(((interval.exited_at or now) - interval.entered_at).total_seconds())
        )
    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "tier": ticket.current_tier,
        "version": ticket.routing_version,
        "owner": person(ticket.owner_id),
        "assignee": person(ticket.assignee_id),
        "first_response_at": ticket.first_response_at,
        "seconds_by_tier": totals,
        "intervals": [
            {
                "tier": row.tier,
                "entered_at": row.entered_at,
                "exited_at": row.exited_at,
                "is_estimated": row.is_estimated,
                "status_history_id": row.status_history_id,
            }
            for row in intervals
        ],
        "events": [
            {
                "id": row.id,
                "kind": row.kind,
                "actor": person(row.actor_id),
                "from_user": person(row.from_user_id),
                "to_user": person(row.to_user_id),
                "from_tier": row.from_tier,
                "to_tier": row.to_tier,
                "reason": row.reason,
                "checked": row.checked,
                "requested": row.requested,
                "created_at": row.created_at,
                "status_history_id": row.status_history_id,
                "return_of_id": row.return_of_id,
            }
            for row in events
        ],
    }
