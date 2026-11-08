"""Explicit related-case links; do not change lifecycle or merge customers."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class TicketLink(Base):
    __tablename__ = "ticket_link"
    __table_args__ = (
        UniqueConstraint("ticket_id", "related_ticket_id", name="uq_ticket_link_pair"),
        CheckConstraint(
            "ticket_id != related_ticket_id", name="ck_ticket_link_not_self"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"), index=True)
    related_ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
