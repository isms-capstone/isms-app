"""Adoption evidence (ADO-01/02, CAP-04): how long real users take to capture a case.

The capture form reports the seconds between the user's first input and saving;
this report summarises them so the 30-second target can be checked on real work
instead of a stopwatch. Only published (non-draft) captures are counted.
"""
from datetime import datetime, timedelta, timezone
from statistics import median

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(tags=["Adoption"])
viewer = RoleChecker(["Admin", "Team Lead", "Executive"])
TARGET_SECONDS = 30
# ADO-04: fields required to create a case. Adding one needs product-owner
# approval (docs/ADO-01-REQUIRED-FIELDS.md) and a change to this list and its test.
REQUIRED_CAPTURE_FIELDS = ("customer", "subject", "channel")


def summary(values):
    if not values:
        return {"count": 0, "median_seconds": None, "p90_seconds": None, "within_target_pct": None}
    ordered = sorted(values)
    p90 = ordered[min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))]
    within = sum(1 for value in ordered if value <= TARGET_SECONDS)
    return {"count": len(ordered), "median_seconds": median(ordered), "p90_seconds": p90,
            "within_target_pct": round(100 * within / len(ordered), 1)}


@router.get("/reports/capture-time")
def capture_time(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), user=Depends(viewer)):
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = db.execute(select(TicketStatusHistory.details, TicketStatusHistory.actor_id)
                      .join(Ticket, Ticket.id == TicketStatusHistory.ticket_id)
                      .where(TicketStatusHistory.created_at >= since, Ticket.status != "DRAFT")).all()
    per_user: dict[int, list[int]] = {}
    for details, actor_id in rows:
        details = details or {}
        seconds = details.get("capture_seconds")
        if details.get("event") == "CASE_CREATED" and isinstance(seconds, int) and actor_id:
            per_user.setdefault(actor_id, []).append(seconds)
    names = {row.id: row.full_name or row.username
             for row in db.scalars(select(User).where(User.id.in_(per_user or [0])))}
    return {
        "target_seconds": TARGET_SECONDS,
        "required_fields": list(REQUIRED_CAPTURE_FIELDS),
        "days": days,
        "overall": summary([value for values in per_user.values() for value in values]),
        "users": sorted(({"user": names.get(user_id, f"#{user_id}"), **summary(values)}
                         for user_id, values in per_user.items()), key=lambda row: row["user"]),
    }
