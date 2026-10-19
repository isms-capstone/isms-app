import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.core.state_machine import validate_status_transition
from app.db.models.ticket import TicketStatus


# 1. ทดสอบ Reopen ภายใน 14 วัน (สำเร็จ)
def test_reopen_within_14_days_success():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    resolved_at = now - timedelta(days=10)
    ticket_data = {
        "reopen_reason": "Problem still occurs",
        "resolved_at": resolved_at
    }
    assert validate_status_transition(
        TicketStatus.RESOLVED,
        TicketStatus.REOPENED,
        user_role="Customer",
        ticket_data=ticket_data
    ) is True


# 2. ทดสอบ Reopen เกิน 14 วัน (ต้องโยน HTTP 400)
def test_reopen_exceed_14_days_fails():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    resolved_at = now - timedelta(days=15)
    ticket_data = {
        "reopen_reason": "Problem still occurs",
        "resolved_at": resolved_at
    }
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.RESOLVED,
            TicketStatus.REOPENED,
            user_role="Customer",
            ticket_data=ticket_data
        )
    assert exc_info.value.status_code == 400
    assert "cannot be reopened after 14 days" in exc_info.value.detail


# 3. ทดสอบ Reopen แบบขาดเหตุผล (ต้องโยน HTTP 422)
def test_reopen_missing_reason_fails():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    resolved_at = now - timedelta(days=5)
    ticket_data = {
        "resolved_at": resolved_at
    }
    with pytest.raises(HTTPException) as exc_info:
        validate_status_transition(
            TicketStatus.RESOLVED,
            TicketStatus.REOPENED,
            user_role="Customer",
            ticket_data=ticket_data
        )
    assert exc_info.value.status_code == 422