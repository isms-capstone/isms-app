"""Validate and persist SIM choices inside the same transaction as the case."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.db.models.similarity_feedback import SimilarityFeedback
from app.db.models.ticket import Ticket
from app.services.ticket_relationships import add_link, find_link
from app.db.models.work_category import TicketAudit


def feedback_for_user(db, feedback_id, user):
    feedback = db.scalar(
        select(SimilarityFeedback)
        .where(SimilarityFeedback.id == feedback_id)
        .with_for_update()
    )
    if feedback is None:
        raise HTTPException(404, "Similarity feedback not found")
    if feedback.created_by_id != user.id:
        raise HTTPException(403, "You cannot use another user’s feedback")
    return feedback


def validate_choice(db, feedback, decision, chosen_id, ticket_id=None):
    if feedback.ticket_id is not None and feedback.ticket_id != ticket_id:
        raise HTTPException(409, "Feedback already belongs to another case")
    if decision not in {"reuse", "link", "new"}:
        raise HTTPException(
            409, "Confirm a similarity decision before creating the case"
        )
    if decision == "new":
        if chosen_id is not None:
            raise HTTPException(422, "New investigation must not include a chosen case")
        return
    ids = {item["ticket_id"] for item in feedback.suggested or []}
    if chosen_id not in ids or chosen_id == ticket_id:
        raise HTTPException(422, "Select a different suggested case")
    selected = db.get(Ticket, chosen_id)
    if selected is None or selected.status in {"DRAFT", "DUPLICATE", "CANCELLED"}:
        raise HTTPException(
            409, "The selected case is no longer available; search again"
        )


def attach_choice(db, feedback, ticket, user):
    validate_choice(
        db, feedback, feedback.decision, feedback.chosen_ticket_id, ticket.id
    )
    feedback.ticket_id = ticket.id
    if feedback.decision == "link":
        chosen_id = feedback.chosen_ticket_id
        if not find_link(db, ticket.id, chosen_id, "related"):
            add_link(db, ticket.id, chosen_id, "related", user.id, "SIM: link to existing case")
    db.add(
        TicketAudit(
            ticket_id=ticket.id,
            actor_id=user.id,
            created_at=datetime.now(UTC).replace(tzinfo=None),
            event="similarity_decision",
            changes={
                "feedback_id": feedback.id,
                "decision": feedback.decision,
                "chosen_ticket_id": feedback.chosen_ticket_id,
            },
        )
    )


def require_publish_decision(db, ticket):
    """Draft publication must not bypass the same guard as direct creation."""
    from app.services.similarity import DECISION_THRESHOLD, search_with_deadline

    query = f"{ticket.subject or ''} {ticket.description or ''}".strip()
    if len(query) < 10:
        return
    existing = db.scalar(
        select(SimilarityFeedback)
        .where(
            SimilarityFeedback.ticket_id == ticket.id,
            SimilarityFeedback.query == query,
            SimilarityFeedback.organization_id == ticket.organization_id,
            SimilarityFeedback.product_instance_id == ticket.product_instance_id,
            SimilarityFeedback.decision.in_(["reuse", "link", "new"]),
        )
        .order_by(SimilarityFeedback.id.desc())
    )
    if existing is not None:
        return
    items = search_with_deadline(
        db.get_bind(),
        q=query,
        organization_id=ticket.organization_id,
        product_instance_id=ticket.product_instance_id,
        exclude_ticket_id=ticket.id,
    )
    if items and any(item["score"] >= DECISION_THRESHOLD for item in items):
        raise HTTPException(
            409,
            "Search similar cases and confirm a decision before publishing the draft",
        )
