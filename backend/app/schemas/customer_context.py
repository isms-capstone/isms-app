from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.customer import Name


class DepartmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    is_active: bool = True


class DepartmentResponse(DepartmentInput):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    organization_id: int


class CourseInput(DepartmentInput):
    kind: Literal["course", "exam"] = "course"


class CourseResponse(CourseInput):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    organization_id: int


class ContractPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_start_date: date | None = None
    contract_end_date: date | None = None


class ContractResponse(ContractPatch):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int


class ExamWindowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    department_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    is_active: bool = True

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_offset(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include timezone offset")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def chronological(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class ExamWindowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    name: str
    department_id: int | None
    starts_at: datetime
    ends_at: datetime
    is_active: bool

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def utc_output(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
