"""Typed relationships between cases."""

from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


TicketLinkType = Literal["duplicate", "related", "follow-up", "caused-by", "child-of"]


class TicketLink(Base):
    __tablename__ = "ticket_link"
    __table_args__ = (
        UniqueConstraint(
            "ticket_id", "related_ticket_id", "relationship_type",
            name="uq_ticket_link_pair_type",
        ),
        CheckConstraint(
            "relationship_type IN ('duplicate', 'related', 'follow-up', 'caused-by', 'child-of')",
            name="ck_ticket_link_type",
        ),
        CheckConstraint(
            "ticket_id != related_ticket_id", name="ck_ticket_link_not_self"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"), index=True)
    related_ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"))
    relationship_type: Mapped[str] = mapped_column(
        String(16), default="related", server_default="related"
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
