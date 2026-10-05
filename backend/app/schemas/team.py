from typing import Optional
from pydantic import BaseModel, ConfigDict

class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class TeamResponse(TeamBase):
     id: int
     model_config = ConfigDict(from_attributes=True)