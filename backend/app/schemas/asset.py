from typing import Optional
from pydantic import BaseModel, Field
from app.db.models.asset import AssetCategory

class AssetBase(BaseModel):
    asset_code: str = Field(..., example="AST-001")
    name: str = Field(..., example="Primary Database Server")
    description: Optional[str] = Field(None, example="Main MariaDB production cluster")
    category: AssetCategory = Field(default=AssetCategory.HARDWARE)
    confidentiality: int = Field(default=1, ge=1, le=3, description="1: Low, 2: Medium, 3: High")
    integrity: int = Field(default=1, ge=1, le=3)
    availability: int = Field(default=1, ge=1, le=3)
    owner_id: Optional[int] = None
    team_id: Optional[int] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[AssetCategory] = None
    confidentiality: Optional[int] = Field(None, ge=1, le=3)
    integrity: Optional[int] = Field(None, ge=1, le=3)
    availability: Optional[int] = Field(None, ge=1, le=3)
    owner_id: Optional[int] = None
    team_id: Optional[int] = None

class AssetResponse(AssetBase):
    id: int

    class Config:
        from_attributes = True
