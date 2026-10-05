from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    modules: Mapped[list["Module"]] = relationship("Module", back_populates="product")
    symptoms: Mapped[list["Symptom"]] = relationship("Symptom", back_populates="product")
    service_stages: Mapped[list["ServiceStage"]] = relationship("ServiceStage", back_populates="product")


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_modules_product_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="modules")
    problem_types: Mapped[list["ProblemType"]] = relationship("ProblemType", back_populates="module")


class ProblemType(Base):
    __tablename__ = "problem_types"
    __table_args__ = (UniqueConstraint("module_id", "name", name="uq_problem_types_module_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    module: Mapped["Module"] = relationship("Module", back_populates="problem_types")


class Symptom(Base):
    __tablename__ = "symptoms"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_symptoms_product_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="symptoms")


class ServiceStage(Base):
    __tablename__ = "service_stages"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_service_stages_product_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="service_stages")


class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CauseCode(Base):
    __tablename__ = "cause_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SolutionCode(Base):
    __tablename__ = "solution_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CaseTemplate(Base):
    __tablename__ = "case_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False, index=True)
    problem_type_id: Mapped[int] = mapped_column(ForeignKey("problem_types.id"), nullable=False, index=True)
    default_severity: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product: Mapped["Product"] = relationship("Product")
    module: Mapped["Module"] = relationship("Module")
    problem_type: Mapped["ProblemType"] = relationship("ProblemType")


class CannedMessage(Base):
    __tablename__ = "canned_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(5000), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SlaPolicy(Base):
    __tablename__ = "sla_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    rules: Mapped[list["SlaPolicyRule"]] = relationship(
        "SlaPolicyRule",
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class SlaPolicyRule(Base):
    __tablename__ = "sla_policy_rules"
    __table_args__ = (
        UniqueConstraint("sla_policy_id", "severity", name="uq_sla_policy_rules_policy_severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sla_policy_id: Mapped[int] = mapped_column(ForeignKey("sla_policies.id"), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    first_response_value: Mapped[int] = mapped_column(Integer, nullable=False)
    first_response_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    resolution_min_value: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_max_value: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    business_hours_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    policy: Mapped["SlaPolicy"] = relationship("SlaPolicy", back_populates="rules")


class BusinessCalendar(Base):
    __tablename__ = "business_calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Bangkok")
    work_start_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(8, 0))
    work_end_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(17, 0))
    monday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    thursday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    friday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    saturday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sunday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    holidays: Mapped[list["BusinessHoliday"]] = relationship(
        "BusinessHoliday",
        back_populates="calendar",
        cascade="all, delete-orphan",
    )


class BusinessHoliday(Base):
    __tablename__ = "business_holidays"
    __table_args__ = (
        UniqueConstraint("business_calendar_id", "holiday_date", name="uq_business_holidays_calendar_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    business_calendar_id: Mapped[int] = mapped_column(ForeignKey("business_calendars.id"), nullable=False, index=True)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    holiday_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ANNUAL")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    calendar: Mapped["BusinessCalendar"] = relationship("BusinessCalendar", back_populates="holidays")
