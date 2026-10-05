from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    save_as_draft: bool = False
    subject: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    channel: Literal['line_oa', 'line_group', 'line_personal', 'portal', 'email', 'phone', 'face_to_face', 'other'] | None = None
    organization_id: int | None = Field(default=None, ge=1)
    contact_id: int | None = Field(default=None, ge=1)
    department_id: int | None = Field(default=None, ge=1)
    course_or_exam_id: int | None = Field(default=None, ge=1)
    product_instance_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    symptom_id: int | None = Field(default=None, ge=1)
    service_stage_id: int | None = Field(default=None, ge=1)
    ticket_type_id: int | None = Field(default=None, ge=1)
    reported_at: datetime | None = None

    @field_validator('subject', 'description')
    @classmethod
    def trim_text(cls, value):
        return value.strip() or None if value is not None else None

    @field_validator('reported_at')
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError('reported_at must include a timezone offset')
        return value


class DraftFieldUpdate(BaseModel):
    """Explicit one-field edit for CAP-06; no autosave or status changes."""
    model_config = ConfigDict(extra='forbid')
    field: Literal['subject', 'description', 'channel', 'organization_id', 'contact_id',
                   'department_id', 'course_or_exam_id', 'product_instance_id', 'module_id',
                   'category_id', 'symptom_id', 'service_stage_id', 'ticket_type_id']
    value: str | int | None


class ReportedTimeUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reported_at: datetime

    @field_validator('reported_at')
    @classmethod
    def timezone_required(cls, value):
        if value.utcoffset() is None:
            raise ValueError('reported_at must include a timezone offset')
        return value


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_no: str | None
    status: str
    subject: str | None
    description: str | None
    channel: str | None
    organization_id: int | None
    contact_id: int | None
    department_id: int | None
    course_or_exam_id: int | None
    product_instance_id: int | None
    module_id: int | None
    category_id: int | None
    symptom_id: int | None
    service_stage_id: int | None
    ticket_type_id: int | None
    owner_id: int | None
    assignee_id: int | None
    created_by_id: int
    reported_at: datetime
    created_at: datetime
    sla_policy_id: int | None
    is_exam_window: bool
    severity: str | None
    current_tier: int | None

    @field_validator('reported_at', 'created_at')
    @classmethod
    def utc_offset(cls, value):
        from datetime import timezone
        return value.replace(tzinfo=timezone.utc) if value.utcoffset() is None else value
