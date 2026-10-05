from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.db.models.automation_rule import AutomationRule
from app.db.models.user import Team
from app.services.automation_rules import apply_automation_rules, rule_matches, validate_rule_definition


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_rule_definition_validation():
    validate_rule_definition("severity", "eq", "assign_team")


def test_rule_matches_integer_field():
    db = make_db()
    team = Team(name="Incident Team")
    db.add(team)
    db.flush()
    rule = AutomationRule(
        name="ExamPlus routing",
        priority=10,
        condition_field="product_id",
        condition_operator="eq",
        condition_value="7",
        action_type="assign_team",
        action_team_id=team.id,
    )
    assert rule_matches(rule, {"product_id": 7}) is True
    assert rule_matches(rule, {"product_id": 8}) is False
    db.close()


def test_apply_active_rule_on_case_create_or_update_payload():
    db = make_db()
    team = Team(name="Incident Team")
    db.add(team)
    db.flush()
    rule = AutomationRule(
        name="S1 routing",
        priority=1,
        condition_field="severity",
        condition_operator="eq",
        condition_value="S1",
        action_type="assign_team",
        action_team_id=team.id,
        is_active=True,
    )
    db.add(rule)
    db.commit()

    result = apply_automation_rules(db, {"severity": "S1", "subject": "Outage"})
    assert result["team_id"] == team.id
    assert result["automation_rule_ids"] == [rule.id]
    db.close()


def test_disabled_rule_does_not_apply():
    db = make_db()
    team = Team(name="Incident Team")
    db.add(team)
    db.flush()
    rule = AutomationRule(
        name="Disabled routing",
        priority=1,
        condition_field="severity",
        condition_operator="eq",
        condition_value="S1",
        action_type="assign_team",
        action_team_id=team.id,
        is_active=False,
    )
    db.add(rule)
    db.commit()

    result = apply_automation_rules(db, {"severity": "S1"})
    assert "team_id" not in result
    assert result["automation_rule_ids"] == []
    db.close()
