from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    team_id: Optional[int] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    team_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
     id: int
     model_config = ConfigDict(from_attributes=True)
