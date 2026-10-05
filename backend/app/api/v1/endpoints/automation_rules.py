from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models.automation_rule import AutomationRule
from app.db.models.user import Team
from app.db.session import get_db
from app.schemas.automation_rule import AutomationRuleCreate, AutomationRuleOut, AutomationRuleUpdate
from app.services.automation_rules import validate_rule_definition

router = APIRouter(prefix="/admin/automation-rules", tags=["Automation Rules"])


def _get_or_404(db: Session, rule_id: int) -> AutomationRule:
    rule = db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation rule not found")
    return rule


def _get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action team not found")
    return team


def _validate_definition(condition_field: str, condition_operator: str, action_type: str) -> None:
    try:
        validate_rule_definition(condition_field, condition_operator, action_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("", response_model=list[AutomationRuleOut], dependencies=[Depends(require_admin)])
def list_automation_rules(
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AutomationRule).order_by(AutomationRule.priority.asc(), AutomationRule.id.asc())
    if active is not None:
        query = query.filter(AutomationRule.is_active.is_(active))
    return query.all()


@router.post("", response_model=AutomationRuleOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_automation_rule(body: AutomationRuleCreate, db: Session = Depends(get_db)):
    _validate_definition(body.condition_field, body.condition_operator, body.action_type)
    _get_team_or_404(db, body.action_team_id)
    rule = AutomationRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AutomationRuleOut, dependencies=[Depends(require_admin)])
def update_automation_rule(
    rule_id: int,
    body: AutomationRuleUpdate,
    db: Session = Depends(get_db),
):
    rule = _get_or_404(db, rule_id)
    data = body.model_dump(exclude_unset=True)
    next_field = data.get("condition_field", rule.condition_field)
    next_operator = data.get("condition_operator", rule.condition_operator)
    next_action = data.get("action_type", rule.action_type)
    _validate_definition(next_field, next_operator, next_action)
    if "action_team_id" in data:
        _get_team_or_404(db, data["action_team_id"])
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", response_model=AutomationRuleOut, dependencies=[Depends(require_admin)])
def disable_automation_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = _get_or_404(db, rule_id)
    rule.is_active = False
    db.commit()
    db.refresh(rule)
    return rule
