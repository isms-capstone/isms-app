from typing import Annotated

from pydantic import BaseModel, ConfigDict, HttpUrl, StringConstraints, field_validator

from app.schemas.customer import Name

Code = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True,
                                      min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9_-]*$")]
Version = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Environment = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True,
                                             min_length=1, max_length=50)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Code
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class ModuleCreate(ProductCreate):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ModuleResponse(ModuleCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    product_id: int


class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    modules: list[ModuleResponse]
    default_team_id: int | None


class InstanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Code
    name: Name
    version: Version
    environment: Environment
    url: HttpUrl
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        if len(str(value)) > 2048:
            raise ValueError("URL must be at most 2048 characters")
        if value.username is not None or value.password is not None:
            raise ValueError("URL must not contain credentials")
        return value


class InstanceResponse(InstanceCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    organization_id: int
    product_id: int
