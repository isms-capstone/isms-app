import pytest
from fastapi import HTTPException
from app.core.state_machine import validate_status_transition
from app.db.models.ticket import TicketStatus


# 1. ทดสอบเปลี่ยนเป็น DUPLICATE โดยระบุ master_ticket_id (สำเร็จ)
def test_transition_to_duplicate_success():
    ticket_data = {"master_ticket_id": 101}
    assert validate_status_transition(
        TicketStatus.NEW,
        TicketStatus.DUPLICATE,
        user_role="Agent",
        ticket_data=ticket_data
    ) is True


# 2. ทดสอบเปลี่ยนเป็น DUPLICATE โดยไม่ระบุ master_ticket_id (ต้องโยน HTTP 422)
def test_transition_to_duplicate_missing_master_fails():
    ticket_data = {}
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.NEW,
            TicketStatus.DUPLICATE,
            user_role="Agent",
            ticket_data=ticket_data
        )
    assert exc_info.value.status_code == 422
    assert "master_ticket_id" in exc_info.value.detail


# 3. ทดสอบเปลี่ยนเป็น CANCELLED โดยระบุ cancel_reason (สำเร็จ)
def test_transition_to_cancelled_success():
    ticket_data = {"cancel_reason": "Created by mistake by user"}
    assert validate_status_transition(
        TicketStatus.NEW,
        TicketStatus.CANCELLED,
        user_role="Agent",
        ticket_data=ticket_data
    ) is True


# 4. ทดสอบเปลี่ยนเป็น CANCELLED โดยไม่ระบุ cancel_reason (ต้องโยน HTTP 422)
def test_transition_to_cancelled_missing_reason_fails():
    ticket_data = {}
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.NEW,
            TicketStatus.CANCELLED,
            user_role="Agent",
            ticket_data=ticket_data
        )
    assert exc_info.value.status_code == 422
    assert "Cancellation reason" in exc_info.value.detail