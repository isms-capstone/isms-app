"""Additive WRK/CAT persistence. All timestamps are UTC."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class TicketWorklog(Base):
    __tablename__ = 'ticket_worklog'
    __table_args__ = (CheckConstraint("kind IN ('internal_note','public_reply')", name='ck_worklog_kind'),
        CheckConstraint("(kind = 'internal_note' AND channel IS NULL) OR (kind = 'public_reply' AND channel IS NOT NULL)", name='ck_worklog_channel'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('ticket.id'), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str | None] = mapped_column(String(50))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TicketAudit(Base):
    __tablename__ = 'ticket_audit'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('ticket.id'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    event: Mapped[str] = mapped_column(String(50))
    changes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TicketTag(Base):
    __tablename__ = 'ticket_tag'
    ticket_id: Mapped[int] = mapped_column(ForeignKey('ticket.id'), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)


class CategoryUsage(Base):
    """Persisted selections, never dropdown views; grouped per user/product/axis."""
    __tablename__ = 'category_usage'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('ticket.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    axis: Mapped[str] = mapped_column(String(32))
    option_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
