"""Case storage matching SRS 10.2 (P1-CAP-01). Times are UTC."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

TICKET_STATUSES = ('DRAFT', 'NEW', 'IN_PROGRESS', 'PENDING_CUSTOMER', 'PENDING_EXTERNAL',
                   'RESOLVED', 'CLOSED', 'REOPENED', 'DUPLICATE', 'CANCELLED')
OPEN_STATUSES = ('NEW', 'IN_PROGRESS', 'PENDING_CUSTOMER', 'PENDING_EXTERNAL', 'REOPENED')


class TicketNumberSequence(Base):
    __tablename__ = 'ticket_number_sequence'
    period: Mapped[str] = mapped_column(String(6), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class Ticket(Base):
    __tablename__ = 'ticket'
    __table_args__ = (
        CheckConstraint('status IN ' + str(TICKET_STATUSES), name='ck_ticket_status'),
        CheckConstraint("severity IS NULL OR severity IN ('S1','S2','S3','S4')", name='ck_ticket_severity'),
        CheckConstraint('current_tier IS NULL OR current_tier IN (0,1,2)', name='ck_ticket_tier'),
        CheckConstraint('reopen_count >= 0', name='ck_ticket_reopen_count'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_no: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), index=True, default='DRAFT')
    ticket_type_id: Mapped[int | None] = mapped_column(ForeignKey('ticket_types.id'))
    channel: Mapped[str | None] = mapped_column(String(50))
    organization_id: Mapped[int | None] = mapped_column(ForeignKey('organization.id'), index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey('contact.id'), index=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey('department.id'))
    course_or_exam_id: Mapped[int | None] = mapped_column(ForeignKey('course_or_exam.id'))
    product_instance_id: Mapped[int | None] = mapped_column(ForeignKey('product_instance.id'), index=True)
    module_id: Mapped[int | None] = mapped_column(ForeignKey('modules.id'))
    environment: Mapped[str | None] = mapped_column(String(50))
    browser_device: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    exam_or_course_context: Mapped[str | None] = mapped_column(String(255))
    category_id: Mapped[int | None] = mapped_column(ForeignKey('problem_types.id'))
    symptom_id: Mapped[int | None] = mapped_column(ForeignKey('symptoms.id'))
    service_stage_id: Mapped[int | None] = mapped_column(ForeignKey('service_stages.id'))
    severity: Mapped[str | None] = mapped_column(String(2))
    impact_scope: Mapped[str | None] = mapped_column(String(50))
    severity_overridden_reason: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    current_tier: Mapped[int | None] = mapped_column(Integer)
    reported_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    root_cause_code_id: Mapped[int | None] = mapped_column(ForeignKey('cause_codes.id'))
    resolution_code_id: Mapped[int | None] = mapped_column(ForeignKey('solution_codes.id'))
    resolution_detail: Mapped[str | None] = mapped_column(Text)
    # KB is Phase 5: reserve the reference, add its FK when that table exists.
    kb_article_id: Mapped[int | None] = mapped_column(Integer)
    master_ticket_id: Mapped[int | None] = mapped_column(ForeignKey('ticket.id'))
    sla_policy_id: Mapped[int | None] = mapped_column(ForeignKey('sla_policies.id'))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    workload_points: Mapped[float | None] = mapped_column(Numeric(10, 2))
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)
    is_exam_window: Mapped[bool] = mapped_column(Boolean, default=False)
    legacy_case_no: Mapped[str | None] = mapped_column(String(100))
