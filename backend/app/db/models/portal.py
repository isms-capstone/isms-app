from sqlalchemy import ForeignKey, String
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
