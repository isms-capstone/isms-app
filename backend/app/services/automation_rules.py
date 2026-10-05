from typing import Any

from sqlalchemy.orm import Session

from app.db.models.automation_rule import AutomationRule


INTEGER_FIELDS = {
    "product_id",
    "module_id",
    "problem_type_id",
    "ticket_type_id",
    "symptom_id",
    "service_stage_id",
}
SUPPORTED_CONDITION_FIELDS = INTEGER_FIELDS | {"severity", "status", "channel"}
SUPPORTED_OPERATORS = {"eq"}
SUPPORTED_ACTIONS = {"assign_team"}


def validate_rule_definition(
    condition_field: str,
    condition_operator: str,
    action_type: str,
) -> None:
    if condition_field not in SUPPORTED_CONDITION_FIELDS:
        raise ValueError(f"Unsupported condition field: {condition_field}")
    if condition_operator not in SUPPORTED_OPERATORS:
        raise ValueError(f"Unsupported condition operator: {condition_operator}")
    if action_type not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported action type: {action_type}")


def _coerce_expected(field: str, value: str) -> Any:
    if field in INTEGER_FIELDS:
        return int(value)
    return value


def rule_matches(rule: AutomationRule, case_data: dict[str, Any]) -> bool:
    actual = case_data.get(rule.condition_field)
    if actual is None:
        return False
    expected = _coerce_expected(rule.condition_field, rule.condition_value)
    return rule.condition_operator == "eq" and actual == expected


def apply_automation_rules(db: Session, case_data: dict[str, Any]) -> dict[str, Any]:
    """Apply enabled routing rules to a case payload.

    The function is intentionally decoupled from a Ticket model so CAP can call
    it during create/update without coupling ADM-06 to a future case schema.
    """
    result = dict(case_data)
    applied_rule_ids: list[int] = []
    rules = (
        db.query(AutomationRule)
        .filter(AutomationRule.is_active.is_(True))
        .order_by(AutomationRule.priority.asc(), AutomationRule.id.asc())
        .all()
    )

    for rule in rules:
        if not rule_matches(rule, result):
            continue
        if rule.action_type == "assign_team":
            result["team_id"] = rule.action_team_id
        applied_rule_ids.append(rule.id)

    result["automation_rule_ids"] = applied_rule_ids
    return result
