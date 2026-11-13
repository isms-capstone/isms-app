"""Atomic relationship, duplicate merge and master-incident operations."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, update

from app.db.models.ticket import Ticket
from app.db.models.ticket_attachment import TicketAttachment
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.ticket_link import TicketLink
from app.db.models.work_category import TicketAudit, TicketWorklog

FINAL_STATUSES = {"CLOSED", "CANCELLED", "DUPLICATE"}
CLOSURE_MESSAGE = "ดำเนินการแก้ไขเรื่องที่แจ้งเรียบร้อยแล้ว"


def find_link(db, source_id, target_id, kind):
    pair = (TicketLink.ticket_id == source_id) & (
        TicketLink.related_ticket_id == target_id
    )
    if kind == "related":
        # SIM rows created before REL may use either direction.
        pair |= (TicketLink.ticket_id == target_id) & (
            TicketLink.related_ticket_id == source_id
        )
    return db.scalar(
        select(TicketLink)
        .where(
            pair,
            TicketLink.relationship_type == kind,
        )
        .order_by(TicketLink.id)
        .limit(1)
    )


def add_link(db, source_id, target_id, kind, actor_id, reason):
    audit_source_id, audit_target_id = source_id, target_id
    if kind == "related":
        source_id, target_id = sorted((source_id, target_id))
    link = TicketLink(
        ticket_id=source_id,
        related_ticket_id=target_id,
        relationship_type=kind,
        actor_id=actor_id,
    )
    db.add(link)
    db.add(
        TicketAudit(
            ticket_id=audit_source_id,
            actor_id=actor_id,
            event="relationship_created",
            changes={
                "related_ticket_id": audit_target_id,
                "relationship_type": kind,
                "reason": reason,
            },
        )
    )
    return link


def lock_pair(db, source_id, target_id):
    if source_id == target_id:
        raise HTTPException(422, "A case cannot be linked to itself")
    rows = db.scalars(
        select(Ticket)
        .where(Ticket.id.in_((source_id, target_id)))
        .order_by(Ticket.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    tickets = {row.id: row for row in rows}
    if source_id not in tickets or target_id not in tickets:
        raise HTTPException(404, "Case not found")
    return tickets[source_id], tickets[target_id]


def require_flat_incident(db, child, master):
    """A case belongs to a single incident and cannot also be a master."""
    if (
        db.scalar(
            select(TicketLink.id)
            .where(
                TicketLink.relationship_type == "child-of",
                (TicketLink.ticket_id.in_((child.id, master.id)))
                | (TicketLink.related_ticket_id == child.id),
            )
            .limit(1)
        )
        is not None
    ):
        raise HTTPException(
            409, "Select a child without an incident and a top-level master"
        )


def move_duplicate_data(db, source, master, actor_id, reason):
    if (
        source.organization_id is None
        or source.organization_id != master.organization_id
    ):
        raise HTTPException(
            422, "Merge duplicate data within the same customer organization"
        )
    if master.status in {"DRAFT", "CANCELLED", "DUPLICATE"}:
        raise HTTPException(422, "Select an active or closed published master case")
    if source.master_ticket_id == master.id and find_link(
        db, source.id, master.id, "duplicate"
    ):
        return
    if master.master_ticket_id and find_link(
        db, master.id, master.master_ticket_id, "duplicate"
    ):
        raise HTTPException(
            409, "Select the primary case rather than an already merged duplicate"
        )
    if (
        db.scalar(
            select(TicketLink.id)
            .where(
                TicketLink.relationship_type == "child-of",
                (TicketLink.ticket_id == master.id)
                | (TicketLink.ticket_id == source.id),
            )
            .limit(1)
        )
        is not None
    ):
        raise HTTPException(
            409, "Use a case that is not already a child of an incident"
        )
    if source.master_ticket_id and find_link(
        db, source.id, source.master_ticket_id, "duplicate"
    ):
        raise HTTPException(409, "This case is already merged into another master")
    if (
        db.scalar(
            select(TicketLink.id)
            .where(
                TicketLink.related_ticket_id == source.id,
                TicketLink.relationship_type.in_(("child-of", "duplicate")),
            )
            .limit(1)
        )
        is not None
    ):
        raise HTTPException(
            409, "A master with linked cases cannot be merged as a duplicate"
        )
    if not find_link(db, source.id, master.id, "duplicate"):
        add_link(db, source.id, master.id, "duplicate", actor_id, reason)
    source.master_ticket_id = master.id
    transfer_duplicate_content(db, source.id, master.id)
    db.add(
        TicketAudit(
            ticket_id=master.id,
            actor_id=actor_id,
            event="duplicate_merged",
            changes={
                "source_ticket_id": source.id,
                "contact_id": source.contact_id,
                "organization_id": source.organization_id,
                "channel": source.channel,
                "reason": reason,
            },
        )
    )


def transfer_duplicate_content(db, source_id, master_id):
    db.execute(
        update(TicketWorklog)
        .where(TicketWorklog.ticket_id == source_id)
        .values(
            ticket_id=master_id,
            original_ticket_id=source_id,
        )
    )
    db.execute(
        update(TicketAttachment)
        .where(TicketAttachment.ticket_id == source_id)
        .values(ticket_id=master_id)
    )


def queue_closure_notice(db, ticket, master_id, actor_id):
    db.add(
        TicketAudit(
            ticket_id=ticket.id,
            actor_id=actor_id,
            event="relationship_closure_notice",
            changes={
                "master_ticket_id": master_id,
                "contact_id": ticket.contact_id,
                "organization_id": ticket.organization_id,
                "channel": ticket.channel,
                "message": CLOSURE_MESSAGE,
                "delivery_status": "pending",
            },
        )
    )


def close_linked_case(db, child, master, target, actor_id, now):
    from app.services.routing import close_interval

    if target == "DUPLICATE":
        transfer_duplicate_content(db, child.id, master.id)
    close_interval(db, child, now)
    db.add(
        TicketStatusHistory(
            ticket_id=child.id,
            from_status=child.status,
            to_status=target,
            actor_id=actor_id,
            created_at=now,
            details={"master_ticket_id": master.id, "reason": "master case closed"},
        )
    )
    child.status = target
    child.closed_at = now
    child.routing_version += 1
    queue_closure_notice(db, child, master.id, actor_id)


def close_relationships(db, master, actor_id, now=None):
    now = now or datetime.now(UTC).replace(tzinfo=None)
    children = db.execute(
        select(Ticket, TicketLink.relationship_type)
        .join(TicketLink, TicketLink.ticket_id == Ticket.id)
        .where(
            TicketLink.related_ticket_id == master.id,
            TicketLink.relationship_type.in_(("duplicate", "child-of")),
        )
        .order_by(Ticket.id)
        .with_for_update()
    ).all()
    pending = {}
    for child, kind in children:
        if child.status in FINAL_STATUSES or child.status == "DRAFT":
            continue
        if kind == "duplicate" and child.master_ticket_id == master.id:
            pending[child.id] = (child, "DUPLICATE")
        elif kind == "child-of":
            pending.setdefault(child.id, (child, "CLOSED"))
    if pending:
        queue_closure_notice(db, master, master.id, actor_id)
    for child, target in pending.values():
        close_linked_case(db, child, master, target, actor_id, now)
