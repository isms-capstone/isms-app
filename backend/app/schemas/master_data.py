from datetime import date, time
from typing import Literal, Optional

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
    sort_order: int = 1


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


class CaseTemplateCreate(MasterDataBase):
    product_id: int
    module_id: int
    problem_type_id: int
    default_severity: Literal["S1", "S2", "S3", "S4"]


class CaseTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    product_id: Optional[int] = None
    module_id: Optional[int] = None
    problem_type_id: Optional[int] = None
    default_severity: Optional[Literal["S1", "S2", "S3", "S4"]] = None
    is_active: Optional[bool] = None


class CaseTemplateOut(CaseTemplateCreate):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class CannedMessageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=5000)
    description: Optional[str] = Field(default=None, max_length=255)


class CannedMessageUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    message: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class CannedMessageOut(CannedMessageCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class SlaPolicyCreate(MasterDataBase):
    pass


class SlaPolicyUpdate(MasterDataUpdate):
    pass


class SlaPolicyOut(MasterDataOut):
    pass


class SlaPolicyRuleCreate(BaseModel):
    severity: Literal["S1", "S2", "S3", "S4"]
    first_response_value: int = Field(gt=0)
    first_response_unit: Literal["MINUTES", "HOURS", "BUSINESS_DAYS"]
    resolution_min_value: int = Field(gt=0)
    resolution_max_value: int = Field(gt=0)
    resolution_unit: Literal["MINUTES", "HOURS", "BUSINESS_DAYS"]
    business_hours_only: bool = True


class SlaPolicyRuleUpdate(BaseModel):
    severity: Optional[Literal["S1", "S2", "S3", "S4"]] = None
    first_response_value: Optional[int] = Field(default=None, gt=0)
    first_response_unit: Optional[Literal["MINUTES", "HOURS", "BUSINESS_DAYS"]] = None
    resolution_min_value: Optional[int] = Field(default=None, gt=0)
    resolution_max_value: Optional[int] = Field(default=None, gt=0)
    resolution_unit: Optional[Literal["MINUTES", "HOURS", "BUSINESS_DAYS"]] = None
    business_hours_only: Optional[bool] = None
    is_active: Optional[bool] = None


class SlaPolicyRuleOut(SlaPolicyRuleCreate):
    id: int
    sla_policy_id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class BusinessCalendarCreate(MasterDataBase):
    timezone: str = Field(default="Asia/Bangkok", min_length=1, max_length=64)
    work_start_time: time = time(8, 0)
    work_end_time: time = time(17, 0)
    monday: bool = True
    tuesday: bool = True
    wednesday: bool = True
    thursday: bool = True
    friday: bool = True
    saturday: bool = False
    sunday: bool = False


class BusinessCalendarUpdate(MasterDataUpdate):
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    monday: Optional[bool] = None
    tuesday: Optional[bool] = None
    wednesday: Optional[bool] = None
    thursday: Optional[bool] = None
    friday: Optional[bool] = None
    saturday: Optional[bool] = None
    sunday: Optional[bool] = None


class BusinessCalendarOut(BusinessCalendarCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class BusinessHolidayCreate(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=150)
    holiday_type: Literal["ANNUAL", "SPECIAL"] = "ANNUAL"
    description: Optional[str] = Field(default=None, max_length=255)


class BusinessHolidayUpdate(BaseModel):
    holiday_date: Optional[date] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    holiday_type: Optional[Literal["ANNUAL", "SPECIAL"]] = None
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class BusinessHolidayOut(BusinessHolidayCreate):
    id: int
    business_calendar_id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
