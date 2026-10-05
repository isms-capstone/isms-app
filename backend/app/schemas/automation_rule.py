from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ConditionField = Literal[
    "product_id",
    "module_id",
    "problem_type_id",
    "ticket_type_id",
    "symptom_id",
    "service_stage_id",
    "severity",
    "status",
    "channel",
]
ConditionOperator = Literal["eq"]
ActionType = Literal["assign_team"]


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    priority: int = Field(default=100, ge=1, le=9999)
    condition_field: ConditionField
    condition_operator: ConditionOperator = "eq"
    condition_value: str = Field(min_length=1, max_length=100)
    action_type: ActionType = "assign_team"
    action_team_id: int = Field(gt=0)


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    priority: Optional[int] = Field(default=None, ge=1, le=9999)
    condition_field: Optional[ConditionField] = None
    condition_operator: Optional[ConditionOperator] = None
    condition_value: Optional[str] = Field(default=None, min_length=1, max_length=100)
    action_type: Optional[ActionType] = None
    action_team_id: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None


class AutomationRuleOut(AutomationRuleCreate):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
