import pytest
from fastapi import HTTPException

from app.core.state_machine import validate_status_transition
from app.db.models.ticket import TicketStatus


def test_valid_draft_to_new():
    valid_data = {
        "contact_id": 1,
        "subject": "System Login Issue",
        "channel": "Web Portal"
    }
    assert validate_status_transition(
        TicketStatus.DRAFT, 
        TicketStatus.NEW, 
        user_role="User", 
        ticket_data=valid_data
    ) is True


def test_invalid_draft_to_new_missing_fields():
    incomplete_data = {"subject": "System Login Issue"}
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.DRAFT, 
            TicketStatus.NEW, 
            user_role="User", 
            ticket_data=incomplete_data
        )
    assert exc_info.value.status_code == 422


def test_invalid_role_transition():
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.NEW, 
            TicketStatus.IN_PROGRESS, 
            user_role="Customer"
        )
    assert exc_info.value.status_code == 403


def test_missing_assignee_condition():
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.NEW, 
            TicketStatus.IN_PROGRESS, 
            user_role="Agent", 
            ticket_data={"assignee_id": None}
        )
    assert exc_info.value.status_code == 422


def test_duplicate_requires_master_ticket():
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.IN_PROGRESS, 
            TicketStatus.DUPLICATE, 
            user_role="Agent", 
            ticket_data={}
        )
    assert exc_info.value.status_code == 422


def test_cancelled_requires_reason():
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.IN_PROGRESS, 
            TicketStatus.CANCELLED, 
            user_role="Agent", 
            ticket_data={}
        )
    assert exc_info.value.status_code == 422