from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
from email_validator import validate_email, EmailNotValidError


class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    team_id: Optional[int] = None
    is_active: Optional[bool] = True

    @field_validator("email")
    @classmethod
    def validate_user_email(cls, value: str) -> str:
        value = value.strip()

        if value.lower().endswith("@isms.local"):
            local_part = value.rsplit("@", 1)[0]

            if not local_part:
                raise ValueError("Invalid email address")

            return value

        try:
            result = validate_email(value, check_deliverability=False)
            return result.normalized
        except EmailNotValidError as exc:
            raise ValueError(str(exc)) from exc


class UserCreate(UserBase):
    password: str
    role: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[int] = None
    is_active: Optional[bool] = None

#Self-service update model for users to update their own profile
class UserSelfUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_user_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = value.strip()

        if value.lower().endswith("@isms.local"):
            local_part = value.rsplit("@", 1)[0]

            if not local_part:
                raise ValueError("Invalid email address")

            return value

        try:
            result = validate_email(value, check_deliverability=False)
            return result.normalized
        except EmailNotValidError as exc:
            raise ValueError(str(exc)) from exc


class UserResponse(UserBase):
    id: int
    role_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)