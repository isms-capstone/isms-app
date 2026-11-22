"""Additive WRK/CAT persistence. All timestamps are UTC."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.db.base_class import Base


class TicketWorklog(Base):
    __tablename__ = 'ticket_worklogs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('ticket.id'), index=True)
    original_ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("ticket.id"), index=True, default=None
    )
    is_internal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default='1')
    message: Mapped[str] = mapped_column(Text)
    body = synonym('message')
    channel: Mapped[str | None] = mapped_column(String(50))
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    actor_id = synonym('author_id')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def kind(self):
        return 'internal_note' if self.is_internal else 'public_reply'

    @kind.setter
    def kind(self, value):
        if value not in ('internal_note', 'public_reply'):
            raise ValueError('Invalid worklog kind')
        self.is_internal = value == 'internal_note'


class TicketAudit(Base):
    __tablename__ = 'ticket_audit'
    __table_args__ = (Index("ix_ticket_audit_created_at_id", "created_at", "id"),)
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
