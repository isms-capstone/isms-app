"""P1-ADM-06: automation rules decide the responsible team on create and edit."""
from sqlalchemy import select

from app.db.models.automation_rule import AutomationRule
from app.db.models.ticket import Ticket
from app.db.models.user import Team
from app.db.models.work_category import TicketAudit
from test_tickets import capture  # noqa: F401


def test_rule_assigns_team_on_create_and_follows_category_edits(capture):
    client, _, factory, data, _ = capture
    with factory() as db:
        exam_team, general_team = Team(name="Exam support"), Team(name="General support")
        db.add_all([exam_team, general_team])
        db.flush()
        db.add(AutomationRule(name="Login problems go to exam support", priority=10,
                              condition_field="problem_type_id", condition_operator="eq",
                              condition_value=str(data["category_id"]), action_type="assign_team",
                              action_team_id=exam_team.id, is_active=True))
        db.add(AutomationRule(name="Phone cases go to general support", priority=5,
                              condition_field="channel", condition_operator="eq",
                              condition_value="phone", action_type="assign_team",
                              action_team_id=general_team.id, is_active=True))
        db.commit()
        exam_id, general_id = exam_team.id, general_team.id

    login = client.post("/api/v1/tickets", json=dict(data, subject="Cannot log in to exam", channel="phone"))
    assert login.status_code == 201, login.text
    # Both rules match; rules run in priority order and the last match wins (ADM-06 contract).
    assert login.json()["team_id"] == exam_id
    with factory() as db:
        audit = db.scalar(select(TicketAudit).where(TicketAudit.ticket_id == login.json()["id"],
                                                    TicketAudit.event == "team_assigned"))
        assert audit and len(audit.changes["automation_rule_ids"]) == 2

    other = dict(data)
    other.pop("category_id")
    plain = client.post("/api/v1/tickets", json=dict(other, subject="Asks for a report export", channel="phone"))
    assert plain.status_code == 201, plain.text
    assert plain.json()["team_id"] == general_id

    # Team filter in the work queue
    with factory() as db:
        assert db.get(Ticket, login.json()["id"]).team_id == exam_id
