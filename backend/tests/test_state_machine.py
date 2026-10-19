import pytest
from fastapi import HTTPException
from app.core.state_machine import validate_status_transition
from app.db.models.ticket import TicketStatus


# --- 1. DRAFT -> NEW ---
def test_draft_to_new_success():
    data = {"contact_id": 1, "subject": "Issue", "channel": "Web"}
    assert validate_status_transition(TicketStatus.DRAFT, TicketStatus.NEW, "User", data) is True

def test_draft_to_new_missing_fields():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(TicketStatus.DRAFT, TicketStatus.NEW, "User", {})
    assert exc.value.status_code == 422


# --- 2. NEW -> IN_PROGRESS ---
def test_new_to_in_progress_success():
    data = {"assignee_id": 10}
    assert validate_status_transition(TicketStatus.NEW, TicketStatus.IN_PROGRESS, "Agent", data) is True

def test_new_to_in_progress_missing_assignee():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(TicketStatus.NEW, TicketStatus.IN_PROGRESS, "Agent", {})
    assert exc.value.status_code == 422


# --- 3. IN_PROGRESS -> PENDING_CUSTOMER & PENDING_EXTERNAL ---
def test_in_progress_to_pending_customer():
    assert validate_status_transition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_CUSTOMER, "Agent") is True

def test_in_progress_to_pending_external_success():
    data = {"pending_external_reason": "Waiting for Vendor response"}
    assert validate_status_transition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_EXTERNAL, "Agent", data) is True

def test_in_progress_to_pending_external_missing_reason():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_EXTERNAL, "Agent", {})
    assert exc.value.status_code == 422


# --- 4. IN_PROGRESS -> RESOLVED ---
def test_in_progress_to_resolved_success():
    data = {
        "category_id": 1,
        "root_cause_code_id": 2,
        "resolution_code_id": 3,
        "product_instance_id": 4
    }
    assert validate_status_transition(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, "Agent", data) is True

def test_in_progress_to_resolved_missing_fields():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, "Agent", {})
    assert exc.value.status_code == 422


# --- 5. RESOLVED -> CLOSED & REOPENED ---
def test_resolved_to_closed():
    assert validate_status_transition(TicketStatus.RESOLVED, TicketStatus.CLOSED, "Customer") is True

def test_resolved_to_reopened_success():
    data = {"reopen_reason": "Issue persists"}
    assert validate_status_transition(TicketStatus.RESOLVED, TicketStatus.REOPENED, "Customer", data) is True

def test_closed_to_reopened_success():
    data = {"reopen_reason": "Found secondary bug"}
    assert validate_status_transition(TicketStatus.CLOSED, TicketStatus.REOPENED, "Customer", data) is True


# --- 6. ANY -> DUPLICATE & CANCELLED ---
def test_any_to_duplicate_success():
    data = {"master_ticket_id": 99}
    assert validate_status_transition(TicketStatus.IN_PROGRESS, TicketStatus.DUPLICATE, "Agent", data) is True

def test_any_to_cancelled_success():
    data = {"cancel_reason": "User created duplicate by mistake"}
    assert validate_status_transition(TicketStatus.NEW, TicketStatus.CANCELLED, "User", data) is True


# --- 7. INVALID TRANSITION & ROLE AUTHORIZATION ---
def test_invalid_direct_transition():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(TicketStatus.DRAFT, TicketStatus.CLOSED, "Admin")
    assert exc.value.status_code == 400

def test_unauthorized_role():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(TicketStatus.NEW, TicketStatus.IN_PROGRESS, "Customer")
    assert exc.value.status_code == 403

