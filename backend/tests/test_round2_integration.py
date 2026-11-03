"""Regression coverage for conflicts found while integrating CORE and CAP."""
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.api.deps import get_current_user
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import Role, User, Team
from app.db.models.master_data import Product
from app.db.models.product import ProductInstance
from app.core.state_machine import validate_status_transition
from test_tickets import capture


def test_status_acl_persistence_and_no_auditor_side_effects(capture):
    client, app, factory, context, _ = capture
    row = client.post('/api/v1/tickets', json=context | {'subject': 'Lifecycle QA', 'channel': 'phone'}).json()
    with factory() as db:
        admin_id = db.scalar(select(User.id).limit(1))
        team = Team(name='Lifecycle support'); db.add(team); db.flush()
        db.get(User, admin_id).team_id = team.id
        instance = db.get(ProductInstance, context['product_instance_id'])
        db.get(Product, instance.product_id).default_team_id = team.id
        db.commit()
    result = client.patch(f"/api/v1/tickets/{row['id']}/status", json={'status': 'IN_PROGRESS', 'assignee_id': admin_id})
    assert result.status_code == 200, result.text
    result = client.patch(f"/api/v1/tickets/{row['id']}/status", json={'status': 'PENDING_EXTERNAL', 'pending_external_reason': 'Waiting for vendor'})
    assert result.status_code == 200, result.text
    with factory() as db:
        assert db.get(Ticket, row['id']).pending_external_reason == 'Waiting for vendor'
        assert len(db.scalars(select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == row['id'])).all()) == 3
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=admin_id, role=SimpleNamespace(name='Auditor'))
    assert client.patch(f"/api/v1/tickets/{row['id']}/status", json={'status': 'CANCELLED', 'cancel_reason': 'forbidden'}).status_code == 403
    with factory() as db:
        assert db.get(Ticket, row['id']).status == 'PENDING_EXTERNAL'


def test_reopen_limit_is_enforced_at_endpoint(capture):
    client, _, factory, context, _ = capture
    row = client.post('/api/v1/tickets', json=context | {'subject': 'Old resolved case', 'channel': 'phone'}).json()
    with factory() as db:
        ticket = db.get(Ticket, row['id']); ticket.status = 'RESOLVED'
        ticket.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=15)
        db.commit()
    assert client.patch(f"/api/v1/tickets/{row['id']}/status", json={'status': 'REOPENED', 'reopen_reason': 'Still broken'}).status_code == 400


def test_resolution_detail_and_unknown_status_cannot_bypass_policy():
    with pytest.raises(HTTPException):
        validate_status_transition('IN_PROGRESS', 'RESOLVED', 'Agent', {'category_id': 1, 'root_cause_code_id': 1, 'resolution_code_id': 1, 'product_instance_id': 1})
    with pytest.raises(HTTPException):
        validate_status_transition('NEW', 'ESCALATED', 'Admin')
