from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MasterDataBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)


class MasterDataUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class MasterDataOut(MasterDataBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(MasterDataBase):
    pass


class ProductUpdate(MasterDataUpdate):
    pass


class ProductOut(MasterDataOut):
    pass


class ProductRefBase(MasterDataBase):
    product_id: int


class ProductRefUpdate(BaseModel):
    product_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class ProductRefOut(MasterDataOut):
    product_id: int


class ModuleRefBase(MasterDataBase):
    module_id: int


class ModuleRefUpdate(BaseModel):
    module_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class ModuleRefOut(MasterDataOut):
    module_id: int


class ServiceStageCreate(ProductRefBase):
    sort_order: int = 0


class ServiceStageUpdate(ProductRefUpdate):
    sort_order: Optional[int] = None


class ServiceStageOut(ProductRefOut):
    sort_order: int


class CodeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)


class CodeUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class CodeOut(CodeCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
