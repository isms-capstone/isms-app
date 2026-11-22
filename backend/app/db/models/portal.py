from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class PortalIdentity(Base):
    __tablename__ = "portal_identity"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), primary_key=True)
    identity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contact.id"))


class PortalSubmission(Base):
    __tablename__ = "portal_submission"

    grant_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("ticket.id", ondelete="CASCADE"))


class PortalEmail(Base):
    __tablename__ = "portal_email"

    worklog_id: Mapped[int] = mapped_column(ForeignKey("ticket_worklogs.id", ondelete="CASCADE"), primary_key=True)
    recipient: Mapped[str] = mapped_column(String(255))


class PortalMagicLink(Base):
    """One-time sign-in link for the self-service portal (POR-09). Only a hash is stored."""
    __tablename__ = "portal_magic_link"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contact.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)


class PortalOutbox(Base):
    """Plain notification e-mails sent by the worker (sign-in links)."""
    __tablename__ = "portal_outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class PortalAnnouncement(Base):
    """Public service status notice, optionally tied to a master incident (POR-10)."""
    __tablename__ = "portal_announcement"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("ticket.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
