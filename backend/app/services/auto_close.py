"""CORE-03 / BR-06: close RESOLVED cases after N business days without a customer objection.

A customer objection is a reopen (REOPENED), which moves the case out of RESOLVED,
so any case still RESOLVED after the delay is closed. Business days follow the
company calendar (weekends and holidays). Cases that breached SLA but have no
breach reason yet (SLA-07) stay RESOLVED, and their owner/assignee is notified
once instead of the case waiting silently. Runs on every routing-worker cycle.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.routing import RoutingPolicy
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User

DEFAULT_DAYS = 3


def configured_days(db: Session) -> int:
    policy = db.get(RoutingPolicy, 1)
    return policy.auto_close_business_days if policy and policy.auto_close_business_days else DEFAULT_DAYS


def run_auto_close_resolved_tickets(db: Session, allowed_business_days: int | None = None, now=None) -> int:
    from app.services.routing import close_interval, notify
    from app.services.sla_engine import schedule_for, sync_clock, update_breach
    from app.services.ticket_relationships import close_relationships

    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    days = allowed_business_days or configured_days(db)
    schedule = schedule_for(db)
    candidates = db.scalars(select(Ticket.id).where(Ticket.status == TicketStatus.RESOLVED,
                                                    Ticket.resolved_at.is_not(None))).all()
    db.commit()
    closed = 0
    for ticket_id in candidates:
        ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update()
                           .execution_options(populate_existing=True))
        if not ticket or ticket.status != TicketStatus.RESOLVED or not ticket.resolved_at:
            db.rollback()
            continue
        try:
            due = schedule.add_business_days(ticket.resolved_at, days)
        except ValueError:
            db.rollback()
            continue
        if now < due:
            db.rollback()
            continue
        if update_breach(db, ticket, now, schedule) and not (ticket.sla_breach_reason or "").strip():
            people = [db.get(User, user_id) for user_id in {ticket.owner_id, ticket.assignee_id} if user_id]
            notify(db, ticket, [user for user in people if user and user.is_active], "auto_close_blocked",
                   f"auto-close-blocked:{ticket.id}:{ticket.resolved_at.isoformat()}",
                   f"{ticket.ticket_no}: ครบกำหนดปิดอัตโนมัติแล้ว แต่เคสเกิน SLA กรุณาระบุเหตุผลแล้วปิดเคส", now)
            db.commit()
            continue
        db.add(TicketStatusHistory(ticket_id=ticket.id, from_status="RESOLVED", to_status="CLOSED",
                                   created_at=now, details={"reason": "ปิดอัตโนมัติ: ครบ "
                                                            f"{days} วันทำการโดยลูกค้าไม่ได้แจ้งกลับ"}))
        close_interval(db, ticket, now)
        sync_clock(db, ticket, now)
        ticket.routing_version += 1
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = now
        sync_clock(db, ticket, now)
        update_breach(db, ticket, now, schedule)
        close_relationships(db, ticket, ticket.owner_id or ticket.created_by_id, now)
        db.commit()
        closed += 1
    return closed
