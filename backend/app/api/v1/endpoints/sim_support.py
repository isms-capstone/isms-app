"""Staff inspection endpoints; never expose internal worklogs to adapters."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker, get_current_user
from app.api.v1.endpoints.customers import get_record
from app.db.models.ticket import Ticket
from app.db.models.ticket_link import TicketLink, TicketLinkType
from app.db.models.user import User
from app.db.session import get_db
from app.services.external_communication import external_replies
from app.services.lifecycle import authorize_case
from app.services.ticket_relationships import (
    FINAL_STATUSES,
    add_link,
    close_linked_case,
    find_link,
    lock_pair,
    move_duplicate_data,
    require_flat_incident,
)

router = APIRouter(
    dependencies=[
        Depends(RoleChecker(["Admin", "Agent", "Specialist", "Developer", "Team Lead"]))
    ]
)
Database = Annotated[Session, Depends(get_db)]


class TicketLinkCreate(BaseModel):
    related_ticket_id: int = Field(gt=0)
    relationship_type: TicketLinkType
    reason: str | None = Field(default=None, max_length=500)


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


@router.post(
    "/tickets/{ticket_id}/links", status_code=201, tags=["Ticket Relationships"]
)
def create_link(
    ticket_id: int,
    body: TicketLinkCreate,
    db: Database,
    user: Annotated[User, Depends(get_current_user)],
):
    """Create a link. Directional types point from this case to the selected case."""
    source, target = lock_pair(db, ticket_id, body.related_ticket_id)
    authorize_case(source, user)
    kind = body.relationship_type
    if find_link(db, source.id, target.id, kind):
        raise HTTPException(409, "This case relationship already exists")
    if kind == "child-of":
        if source.status in FINAL_STATUSES | {
            "DRAFT"
        } or target.status in FINAL_STATUSES | {"DRAFT"}:
            raise HTTPException(422, "Select two active published cases")
        require_flat_incident(db, source, target)
    link = add_link(
        db, source.id, target.id, kind, user.id, body.reason or "Manual relationship"
    )
    db.commit()
    db.refresh(link)
    return link


class DuplicateMerge(BaseModel):
    master_ticket_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)


@router.post("/tickets/{ticket_id}/merge-duplicate", tags=["Ticket Relationships"])
def merge_duplicate(
    ticket_id: int,
    body: DuplicateMerge,
    db: Database,
    user: Annotated[User, Depends(get_current_user)],
):
    source, master = lock_pair(db, ticket_id, body.master_ticket_id)
    authorize_case(source, user)
    authorize_case(master, user)
    if not body.reason.strip():
        raise HTTPException(422, "Enter a reason")
    if source.status == "DUPLICATE" and source.master_ticket_id == master.id:
        return {"status": source.status}
    if source.status in FINAL_STATUSES | {"DRAFT"}:
        raise HTTPException(422, "Select an active published source case")
    move_duplicate_data(db, source, master, user.id, body.reason.strip())
    if master.status == "CLOSED":
        close_linked_case(
            db,
            source,
            master,
            "DUPLICATE",
            user.id,
            datetime.now(UTC).replace(tzinfo=None),
        )
    db.commit()
    return {"status": source.status}
