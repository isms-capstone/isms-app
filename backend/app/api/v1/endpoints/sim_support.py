"""Staff inspection endpoints; never expose internal worklogs to adapters."""

from typing import Annotated, Literal

from app.api.deps import RoleChecker
from app.api.v1.endpoints.customers import get_record
from app.db.models.ticket import Ticket
from app.db.models.ticket_link import TicketLink
from app.db.session import get_db
from app.services.external_communication import external_replies
from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

router = APIRouter(
    dependencies=[
        Depends(RoleChecker(["Admin", "Agent", "Specialist", "Developer", "Team Lead"]))
    ]
)
Database = Annotated[Session, Depends(get_db)]


@router.get("/tickets/{ticket_id}/external-replies/{channel}")
def delivery_preview(
    ticket_id: int, channel: Literal["portal", "line", "email"], db: Database
):
    get_record(db, Ticket, ticket_id)
    # Customer authorization belongs in the future delivery adapter. This endpoint
    # is staff-only, and even its response excludes internal notes by SQL.
    return external_replies(db, ticket_id, channel)


@router.get("/tickets/{ticket_id}/links")
def links(ticket_id: int, db: Database):
    get_record(db, Ticket, ticket_id)
    return db.scalars(
        select(TicketLink).where(
            or_(
                TicketLink.ticket_id == ticket_id,
                TicketLink.related_ticket_id == ticket_id,
            )
        )
    ).all()
