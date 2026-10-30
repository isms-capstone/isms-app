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
    for ticket in resolved_tickets:
        if ticket.resolved_at and is_auto_close_eligible(ticket.resolved_at, now, allowed_business_days):
            db.add(TicketStatusHistory(ticket_id=ticket.id, from_status='RESOLVED', to_status='CLOSED',
                                      created_at=now, details={'reason': 'automatic business-day closure'}))
            ticket.status = TicketStatus.CLOSED
            ticket.closed_at = now
            closed_count += 1

    if closed_count > 0:
        db.commit()
        
    return closed_count
