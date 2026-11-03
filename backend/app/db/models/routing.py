"""ESC state and append-only evidence. Existing teams/products remain canonical."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class TeamRouting(Base):
    __tablename__ = "team_routing"
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class ProductTierRoute(Base):
    __tablename__ = "product_tier_route"
    __table_args__ = (
        UniqueConstraint("product_id", "tier", name="uq_product_tier_route"),
        CheckConstraint("tier IN (0,1,2)", name="ck_route_tier"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    tier: Mapped[int] = mapped_column(Integer)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))


class RoutingPolicy(Base):
    __tablename__ = "routing_policy"
    __table_args__ = (
        CheckConstraint("s1_minutes BETWEEN 1 AND 1440", name="ck_routing_s1_minutes"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    s1_minutes: Mapped[int] = mapped_column(Integer, default=15)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    business_calendar_id: Mapped[int | None] = mapped_column(
        ForeignKey("business_calendars.id")
    )


class RoutingEvent(Base):
    __tablename__ = "routing_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"), index=True)
    status_history_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_status_history.id")
    )
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(30))
    from_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    from_tier: Mapped[int] = mapped_column(Integer)
    to_tier: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    checked: Mapped[str | None] = mapped_column(Text)
    requested: Mapped[str | None] = mapped_column(Text)
    return_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("routing_event.id"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TierInterval(Base):
    __tablename__ = "ticket_tier_interval"
    __table_args__ = (CheckConstraint("tier IN (0,1,2)", name="ck_interval_tier"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"), index=True)
    open_ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("ticket.id"), unique=True
    )
    tier: Mapped[int] = mapped_column(Integer)
    entered_at: Mapped[datetime] = mapped_column(DateTime)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime)
    status_history_id: Mapped[int | None] = mapped_column(
        ForeignKey("ticket_status_history.id")
    )
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)


class RoutingNotification(Base):
    __tablename__ = "routing_notification"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(180), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)


class RoutingJobLease(Base):
    __tablename__ = "routing_job_lease"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    locked_until: Mapped[datetime] = mapped_column(DateTime)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)
