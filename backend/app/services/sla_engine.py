"""SLA clock, policy selection and scheduled in-app notifications."""
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.sla_calendar import Schedule
from app.db.models.customer_context import ExamWindow
from app.db.models.master_data import BusinessCalendar, SlaPolicy
from app.db.models.product import Product, ProductInstance
from app.db.models.sla import SlaClock
from app.db.models.ticket import OPEN_STATUSES, Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User

LEVELS = ("S1", "S2", "S3", "S4")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
COUNTING = frozenset(OPEN_STATUSES) - {"PENDING_CUSTOMER"}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def schedule_for(db):
    calendar = db.scalar(select(BusinessCalendar).options(selectinload(BusinessCalendar.holidays))
                         .where(BusinessCalendar.name == "Thailand Business Calendar",
                                BusinessCalendar.is_active.is_(True)))
    if calendar is None:
        return Schedule()
    return Schedule(calendar.timezone, calendar.work_start_time, calendar.work_end_time,
                    tuple(getattr(calendar, day) for day in WEEKDAYS),
                    frozenset(row.holiday_date for row in calendar.holidays if row.is_active))


def rule_for(db, ticket):
    policy_id = None
    if ticket.product_instance_id:
        policy_id = db.scalar(select(Product.sla_policy_id).join(ProductInstance)
                              .where(ProductInstance.id == ticket.product_instance_id))
    policy = db.get(SlaPolicy, policy_id) if policy_id else None
    if policy and policy.is_active:
        rule = next((rule for rule in policy.rules
                     if rule.is_active and rule.severity == ticket.severity), None)
        if rule:
            return rule
    default = db.scalar(select(SlaPolicy).where(
        SlaPolicy.name == "Default SLA Policy", SlaPolicy.is_active.is_(True)))
    if default:
        return next((rule for rule in default.rules
                     if rule.is_active and rule.severity == ticket.severity), None)
    return None


def apply_exam_window(db, ticket, now):
    if ticket.status == "DRAFT":
        return
    inside = ticket.organization_id is not None and db.scalar(select(ExamWindow.id).where(
        ExamWindow.organization_id == ticket.organization_id, ExamWindow.is_active.is_(True),
        ExamWindow.starts_at <= ticket.reported_at, ExamWindow.ends_at > ticket.reported_at,
        or_(ExamWindow.department_id.is_(None), ExamWindow.department_id == ticket.department_id),
    ).limit(1)) is not None
    if inside or ticket.sla_exam_base_severity:
        ticket.is_exam_window = inside
    base = ticket.sla_exam_base_severity
    if base and ticket.severity != LEVELS[LEVELS.index(base) - 1]:
        base = None
        ticket.sla_exam_base_severity = None
    if not inside and base:
        ticket.severity = base
        ticket.sla_exam_base_severity = None
    if inside and not base and ticket.impact_scope and not ticket.severity_overridden_reason:
        from app.services.categorization import suggest_severity

        normal = suggest_severity(ticket.impact_scope, False)
        if ticket.severity == suggest_severity(ticket.impact_scope, True):
            ticket.severity = normal
    if inside and not base and ticket.severity in LEVELS[1:]:
        from app.services.routing import leaders, notify

        base = ticket.severity
        ticket.sla_exam_base_severity = base
        ticket.severity = LEVELS[LEVELS.index(base) - 1]
        notify(db, ticket, leaders(db, ticket), "sla_exam_upgrade",
               f"sla-exam:{ticket.id}:{base}",
               f"{ticket.ticket_no}: exam window priority raised from {base} to {ticket.severity}", now)


def intervals_for(db, ticket):
    """Reconstruct legacy intervals from actual transitions when no clock has been stored."""
    stored = db.scalars(select(SlaClock).where(SlaClock.ticket_id == ticket.id)
                        .order_by(SlaClock.id)).all()
    if stored or ticket.status == "DRAFT":
        return stored
    history = db.scalars(select(TicketStatusHistory).where(
        TicketStatusHistory.ticket_id == ticket.id,
        TicketStatusHistory.from_status != TicketStatusHistory.to_status,
    ).order_by(TicketStatusHistory.created_at, TicketStatusHistory.id)).all()
    started = ticket.reported_at
    status = history[0].from_status if history else ticket.status
    intervals = []
    for event in history:
        if status != "DRAFT":
            ended = max(started, event.created_at)
            intervals.append(SlaClock(ticket_id=ticket.id, status=status, started_at=started, ended_at=ended))
            started = ended
        status = event.to_status
    if not intervals and ticket.status in {"RESOLVED", "CLOSED"} and ticket.resolved_at:
        ended = max(started, ticket.resolved_at)
        intervals.append(SlaClock(ticket_id=ticket.id, status="NEW", started_at=started, ended_at=ended))
        started = ended
    intervals.append(SlaClock(ticket_id=ticket.id, status=ticket.status, started_at=started))
    return intervals


def sync_clock(db, ticket, now):
    rows = intervals_for(db, ticket)
    if not rows:
        return
    db.add_all(rows)
    rule = rule_for(db, ticket)
    ticket.sla_policy_id = rule.sla_policy_id if rule else None
    first = rows[0]
    first.started_at = min(ticket.reported_at, first.ended_at or now)
    last = rows[-1]
    if last.status != ticket.status:
        last.ended_at = max(last.started_at, now)
        db.add(SlaClock(ticket_id=ticket.id, status=ticket.status, started_at=last.ended_at))


def measurement(db, ticket, now=None, schedule=None):
    now = now or utcnow()
    rule = rule_for(db, ticket)
    if not rule or ticket.status == "DRAFT":
        return None
    schedule = schedule or schedule_for(db)
    intervals = intervals_for(db, ticket)
    business = ticket.severity != "S1"
    units = {"MINUTES": 60, "HOURS": 3600,
             "BUSINESS_DAYS": schedule.day_seconds if business else 86400}

    def metric(value, unit, stop, finished):
        target = value * units[unit]
        elapsed = 0
        for row in intervals:
            if row.status not in COUNTING:
                continue
            end = min(row.ended_at or now, stop or now)
            elapsed += (schedule.seconds(row.started_at, end) if business
                        else max(0, int((end - row.started_at).total_seconds())))
        return {"target_seconds": target, "elapsed_seconds": elapsed,
                "remaining_seconds": target - elapsed, "finished": finished,
                "breached": elapsed > target}

    terminal = ticket.status not in OPEN_STATUSES
    response = metric(rule.first_response_value, rule.first_response_unit,
                      ticket.first_response_at, bool(ticket.first_response_at) or terminal)
    resolution = metric(rule.resolution_max_value, rule.resolution_unit, ticket.resolved_at if terminal else None, terminal)
    pending = ticket.status == "PENDING_CUSTOMER"
    active = None if terminal or pending else min(
        (metric for metric in (response, resolution) if not metric["finished"]),
        key=lambda metric: metric["remaining_seconds"],
    )
    return {"first_response": response, "resolution": resolution, "paused": pending,
            "remaining_seconds": active["remaining_seconds"] if active else None,
            "remaining_ratio": active["remaining_seconds"] / active["target_seconds"] if active else None,
            "breached": bool(ticket.sla_breached or response["breached"] or resolution["breached"])}


def update_breach(db, ticket, now):
    state = measurement(db, ticket, now)
    ticket.sla_breached = ticket.sla_breached or bool(state and state["breached"])
    return ticket.sla_breached


def run_sla_checks(db, now=None):
    from app.services.routing import leaders, notify

    now = now or utcnow()
    schedule = schedule_for(db)
    ids = db.scalars(select(Ticket.id).where(Ticket.status.in_(OPEN_STATUSES))).all()
    db.commit()
    count = 0
    for ticket_id in ids:
        ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
        if not ticket or ticket.status not in OPEN_STATUSES:
            db.rollback()
            continue
        sync_clock(db, ticket, now)
        state = measurement(db, ticket, now, schedule)
        recipients = leaders(db, ticket)
        responsible_id = ticket.assignee_id or ticket.owner_id
        responsible = db.get(User, responsible_id) if responsible_id else None
        recipients = list({user.id: user for user in [*recipients, responsible] if user and user.is_active}.values())
        if state:
            ticket.sla_breached = ticket.sla_breached or state["breached"]
            for name in ("first_response", "resolution"):
                clock = state[name]
                if state["paused"] or (clock["finished"] and not clock["breached"]):
                    continue
                elapsed, target = clock["elapsed_seconds"], clock["target_seconds"]
                for threshold in (50, 75, 100):
                    crossed = elapsed > target if threshold == 100 else elapsed * 100 >= target * threshold
                    if crossed:
                        count += notify(db, ticket, recipients, "sla_breach" if threshold == 100 else "sla_warning",
                                        f"sla:{ticket.id}:{name}:{threshold}",
                                        f"{ticket.ticket_no}: SLA {name.replace('_', ' ')} {threshold}%", now)
        if ticket.status == "PENDING_CUSTOMER" and schedule.day_seconds > 0:
            pause = intervals_for(db, ticket)[-1]
            cycle = schedule.seconds(pause.started_at, now) // (2 * schedule.day_seconds)
            if cycle:
                count += notify(db, ticket, recipients, "sla_customer_followup",
                                f"sla-followup:{ticket.id}:{pause.id}:{cycle}",
                                f"{ticket.ticket_no}: Follow up with customer ({ticket.pending_customer_reason or 'awaiting reply'})"[:1000], now)
        db.commit()
    return count
