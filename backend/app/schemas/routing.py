from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]
Tier = Literal[0, 1, 2]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RouteInput(Strict):
    product_id: int = Field(ge=1)
    tier: Tier
    team_id: int = Field(ge=1)


class LeaderInput(Strict):
    leader_id: int = Field(ge=1)


class UserTierInput(Strict):
    default_tier: Tier


class PolicyInput(Strict):
    s1_minutes: int = Field(ge=1, le=1440)
    enabled: bool = True
    business_calendar_id: int | None = Field(default=None, ge=1)


class Versioned(Strict):
    expected_version: int = Field(ge=0)


class HandoffInput(Versioned):
    assignee_id: int = Field(ge=1)
    tier: Tier
    reason: Text
    checked: Text
    requested: Text


class ReturnInput(Versioned):
    event_id: int = Field(ge=1)
    reason: Text


class AssignInput(Versioned):
    assignee_id: int = Field(ge=1)
    reason: Text


class AvailabilityInput(Strict):
    is_available: bool


class BulkInput(Strict):
    assignee_id: int = Field(ge=1)
    reason: Text
    ticket_ids: list[int] = Field(min_length=1, max_length=1000)
