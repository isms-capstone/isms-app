from typing import Optional
from pydantic import BaseModel, ConfigDict

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class RoleOut(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)