import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Impact = Literal['organization', 'group', 'single_user', 'non_disruptive']
Severity = Literal['S1', 'S2', 'S3', 'S4']


class CategoryFields(BaseModel):
    model_config = ConfigDict(extra='forbid')
    impact_scope: Impact | None = None
    is_exam_window: bool | None = None
    severity: Severity | None = None
    severity_overridden_reason: str | None = Field(default=None, max_length=2000)
    root_cause_code_id: int | None = Field(default=None, ge=1)
    root_cause_detail: str | None = Field(default=None, max_length=20000)
    resolution_code_id: int | None = Field(default=None, ge=1)
    resolution_detail: str | None = Field(default=None, max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator('severity_overridden_reason', 'root_cause_detail', 'resolution_detail')
    @classmethod
    def trim(cls, value):
        return value.strip() or None if value is not None else None

    @field_validator('tags')
    @classmethod
    def normalize_tags(cls, values):
        result = []
        for value in values:
            value = unicodedata.normalize('NFC', value).strip().casefold()
            if not value or len(value) > 64 or any(unicodedata.category(c).startswith('C') for c in value):
                raise ValueError('Tags must contain 1-64 printable characters')
            if value not in result:
                result.append(value)
        return result


class CategorizationUpdate(CategoryFields):
    product_instance_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    symptom_id: int | None = Field(default=None, ge=1)
    service_stage_id: int | None = Field(default=None, ge=1)
    ticket_type_id: int | None = Field(default=None, ge=1)
