"""Idempotent scheduled checks. Alerts are durable in-app records, not external messages."""

from datetime import UTC, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update

from app.db.models.master_data import BusinessCalendar, BusinessHoliday
from app.db.models.routing import (
    RoutingEvent,
    RoutingJobLease,
    RoutingPolicy,
    TeamRouting,
)
from app.db.models.ticket import OPEN_STATUSES, Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.services import routing


def within_business_hours(db, now, calendar_id):
    calendar = db.get(BusinessCalendar, calendar_id) if calendar_id else None
    if calendar_id and (calendar is None or not calendar.is_active):
        return False
    zone = ZoneInfo(calendar.timezone) if calendar else timezone(timedelta(hours=7))
    local = now.replace(tzinfo=UTC).astimezone(zone)
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    working = (
        getattr(calendar, weekdays[local.weekday()])
        if calendar
        else local.weekday() < 5
    )
    if not working:
        return False
    if calendar and db.scalar(
        select(BusinessHoliday.id).where(
            BusinessHoliday.business_calendar_id == calendar.id,
            BusinessHoliday.holiday_date == local.date(),
            BusinessHoliday.is_active.is_(True),
        )
    ):
        return False
    start, end = (
        (calendar.work_start_time, calendar.work_end_time)
        if calendar
        else (time(8), time(17))
    )
    return start <= local.time().replace(tzinfo=None) < end


def ensure_lease(db):
    table = RoutingJobLease.__table__
    values = {"id": 1, "locked_until": datetime(1970, 1, 1)}
    if db.bind.dialect.name == "mysql":
        from sqlalchemy.dialects.mysql import insert

        statement = insert(table).values(**values).on_duplicate_key_update(id=1)
    else:
        from sqlalchemy.dialects.sqlite import insert

        statement = (
            insert(table).values(**values).on_conflict_do_nothing(index_elements=["id"])
        )
    db.execute(statement)


def run_routing_checks(db, now=None):
    # MariaDB DATETIME has second precision; the lease token must round-trip exactly.
    now = (now or routing.utcnow()).replace(microsecond=0)
    ensure_lease(db)
    token = now + timedelta(minutes=9)
    claimed = db.execute(
        update(RoutingJobLease)
        .where(RoutingJobLease.id == 1, RoutingJobLease.locked_until <= now)
        .values(locked_until=token)
    ).rowcount
    db.commit()
    if not claimed:
        return {
            "skipped": "another worker owns the lease",
            "escalated": 0,
            "new_alerts": 0,
        }
    result = {"escalated": 0, "new_alerts": 0}
    try:
        policy = db.get(RoutingPolicy, 1)
        enabled = policy.enabled if policy else True
        minutes = policy.s1_minutes if policy else 15
        calendar_id = policy.business_calendar_id if policy else None
        business = within_business_hours(db, now, calendar_id)
        tickets = db.scalars(
            select(Ticket)
            .where(Ticket.status.in_(OPEN_STATUSES))
            .order_by(Ticket.id)
            .with_for_update()
        ).all()
        for ticket in tickets:
            recipients = routing.leaders(db, ticket)
            published_at = db.scalar(
                select(TicketStatusHistory.created_at)
                .where(
                    TicketStatusHistory.ticket_id == ticket.id,
                    TicketStatusHistory.from_status == "DRAFT",
                    TicketStatusHistory.to_status == "NEW",
                )
                .order_by(TicketStatusHistory.id.desc())
                .limit(1)
            )
            queue_started_at = published_at or ticket.created_at
            if (
                business
                and ticket.status == "NEW"
                and now - queue_started_at > timedelta(minutes=15)
            ):
                result["new_alerts"] += routing.notify(
                    db,
                    ticket,
                    recipients,
                    "new_stalled",
                    f"new:{ticket.id}:{queue_started_at.isoformat()}",
                    f"{ticket.ticket_no}: NEW ค้างเกิน 15 นาที กรุณาตรวจสอบผู้รับผิดชอบ",
                    now,
                )
            if (
                not enabled
                or ticket.severity != "S1"
                or ticket.first_response_at is not None
            ):
                continue
            previous = db.scalar(
                select(RoutingEvent)
                .where(
                    RoutingEvent.ticket_id == ticket.id,
                    RoutingEvent.kind.in_(["handoff", "auto_escalate", "return"]),
                )
                .order_by(RoutingEvent.id.desc())
                .limit(1)
            )
            baseline = (
                max(queue_started_at, previous.created_at)
                if previous
                else queue_started_at
            )
            if now - baseline <= timedelta(minutes=minutes):
                continue
            key = f"s1:{ticket.id}:{ticket.routing_version}:{baseline.isoformat()}"
            routing.notify(
                db,
                ticket,
                recipients,
                "s1_unresponsive",
                key,
                f"{ticket.ticket_no}: S1 ไม่มีการตอบสนองเกิน {minutes} นาที",
                now,
            )
            tier = ticket.current_tier if ticket.current_tier is not None else 2
            if tier == 0:
                continue
            team_id = routing.route_team(db, ticket, tier - 1)
            candidates = (
                db.scalars(
                    select(User)
                    .where(
                        User.team_id == team_id,
                        User.default_tier == tier - 1,
                        User.is_active.is_(True),
                        User.is_available.is_(True),
                    )
                    .order_by(User.id)
                ).all()
                if team_id
                else []
            )
            candidates = [
                user
                for user in candidates
                if routing.role(user) in routing.SUPPORT_ROLES
            ]
            if not candidates:
                routing.notify(
                    db,
                    ticket,
                    recipients,
                    "routing_blocked",
                    "blocked:" + key,
                    f"{ticket.ticket_no}: ส่งต่ออัตโนมัติไม่ได้ กรุณาตั้งทีม Tier {tier - 1} และผู้พร้อมรับงาน",
                    now,
                )
                continue
            leader = db.get(TeamRouting, team_id)
            target = next(
                (user for user in candidates if leader and user.id == leader.leader_id),
                candidates[0],
            )
            routing.claim_version(db, ticket, ticket.routing_version)
            routing.record(
                db,
                ticket,
                target,
                tier - 1,
                None,
                "auto_escalate",
                f"S1 ไม่มีการตอบสนองเกิน {minutes} นาที",
                checked="Scheduled first-response check",
                requested="Urgent response and investigation",
                now=now,
            )
            routing.notify(
                db,
                ticket,
                [target],
                "auto_escalated",
                f"destination:{key}",
                f"{ticket.ticket_no}: ได้รับเคส S1 ส่งต่ออัตโนมัติ กรุณาตอบสนอง",
                now,
            )
            result["escalated"] += 1
        # Only the worker holding this token can release the lease.
        db.execute(
            update(RoutingJobLease)
            .where(RoutingJobLease.id == 1, RoutingJobLease.locked_until == token)
            .values(locked_until=now + timedelta(minutes=5), last_success_at=now)
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        db.execute(
            update(RoutingJobLease)
            .where(RoutingJobLease.id == 1, RoutingJobLease.locked_until == token)
            .values(locked_until=now)
        )
        db.commit()
        raise
