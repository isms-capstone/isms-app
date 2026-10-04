from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, TypeAdapter, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ChannelType = Literal["line_user_id", "line_group_id", "email", "phone"]


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    is_active: bool = True


class OrganizationResponse(OrganizationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    is_active: bool = True


class ChannelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel_type: ChannelType
    value: Name

    @model_validator(mode="after")
    def validate_email_channel(self):
        if self.channel_type == "email":
            self.value = str(TypeAdapter(EmailStr).validate_python(self.value)).casefold()
        return self


class ChannelResponse(ChannelCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contact_id: int


class ContactResponse(ContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    channels: list[ChannelResponse]
