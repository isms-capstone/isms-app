from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.ticket import Ticket, TicketStatus
from app.core.working_days import is_auto_close_eligible
from app.db.models.ticket_history import TicketStatusHistory

def run_auto_close_resolved_tickets(db: Session, allowed_business_days: int = 3) -> int:
    """
    ตรวจและปิดเคส RESOLVED อัตโนมัติเมื่อครบกำหนดวันทำการที่ตั้งค่าไว้
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # ดึงเฉพาะเคสสถานะ RESOLVED
    stmt = select(Ticket).where(Ticket.status == TicketStatus.RESOLVED)
    resolved_tickets = db.scalars(stmt).all()
    
    closed_count = 0
    from app.services.sla_engine import sync_clock, update_breach

    for ticket in resolved_tickets:
        ticket = db.scalar(select(Ticket).where(Ticket.id == ticket.id)
                           .with_for_update().execution_options(populate_existing=True))
        if not ticket or ticket.status != TicketStatus.RESOLVED:
            continue
        if ticket.resolved_at and is_auto_close_eligible(ticket.resolved_at, now, allowed_business_days):
            if update_breach(db, ticket, now) and not (ticket.sla_breach_reason or '').strip():
                continue
            db.add(TicketStatusHistory(ticket_id=ticket.id, from_status='RESOLVED', to_status='CLOSED',
                                      created_at=now, details={'reason': 'automatic business-day closure'}))
            from app.services.routing import close_interval
            close_interval(db, ticket, now)
            sync_clock(db, ticket, now)
            ticket.routing_version += 1
            ticket.status = TicketStatus.CLOSED
            ticket.closed_at = now
            sync_clock(db, ticket, now)
            closed_count += 1

    if closed_count > 0:
        db.commit()
        
    return closed_count
