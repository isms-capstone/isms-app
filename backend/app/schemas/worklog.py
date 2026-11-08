from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Channel = Literal['line_oa', 'line_group', 'line_personal', 'portal', 'email', 'phone', 'face_to_face', 'other']


class WorklogCreate(BaseModel):
    """Canonical API with explicit, non-ambiguous legacy aliases."""
    model_config = ConfigDict(extra='forbid')
    kind: Literal['internal_note', 'public_reply']
    body: str = Field(min_length=1, max_length=20000)
    channel: Channel | None = None

    @model_validator(mode='before')
    @classmethod
    def legacy_fields(cls, values):
        if isinstance(values, dict) and ('message' in values or 'is_internal' in values):
            values = dict(values)
            if 'body' in values or 'kind' in values:
                raise ValueError('Use one worklog field format, not both')
            internal = values.pop('is_internal', True)
            if not isinstance(internal, bool):
                raise ValueError('is_internal must be boolean')
            values['kind'] = 'internal_note' if internal else 'public_reply'
            if 'message' in values:
                values['body'] = values.pop('message')
        return values

    @field_validator('body')
    @classmethod
    def trim_body(cls, value):
        if not value.strip():
            raise ValueError('Message must not be blank')
        return value.strip()

    @model_validator(mode='after')
    def validate_channel(self):
        if (self.kind == 'public_reply') != (self.channel is not None):
            raise ValueError('Public replies require the actual delivery channel; internal notes have no external channel')
        return self
