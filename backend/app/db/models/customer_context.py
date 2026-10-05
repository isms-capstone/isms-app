"""Reusable customer context and important calendar windows."""
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
    Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Department(Base):
    __tablename__ = "department"
    __table_args__ = (
        UniqueConstraint("organization_id", "name_key", name="uq_department_name"),
        UniqueConstraint("organization_id", "id", name="uq_department_org_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    name_key: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CourseOrExam(Base):
    __tablename__ = "course_or_exam"
    __table_args__ = (
        UniqueConstraint("organization_id", "kind", "name_key", name="uq_course_exam_name"),
        CheckConstraint("kind IN ('course', 'exam')", name="ck_course_exam_kind"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    name_key: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExamWindow(Base):
    __tablename__ = "exam_window"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "department_id"],
                             ["department.organization_id", "department.id"],
                             name="fk_exam_window_department_org"),
        CheckConstraint("ends_at > starts_at", name="ck_exam_window_range"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    # Store UTC without offset in MariaDB; API requires offset-aware input.
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
