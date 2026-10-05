"""Customer registry (P1-CUSPRD-01). No dependency on ADM tables."""
from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = (
        CheckConstraint("contract_start_date IS NULL OR contract_end_date IS NULL OR contract_end_date >= contract_start_date", name="ck_organization_contract_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    contract_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contacts: Mapped[list["Contact"]] = relationship(back_populates="organization")


class Contact(Base):
    __tablename__ = "contact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization: Mapped[Organization] = relationship(back_populates="contacts")
    channels: Mapped[list["ChannelIdentity"]] = relationship(back_populates="contact")


class ChannelIdentity(Base):
    __tablename__ = "channel_identity"
    __table_args__ = (
        UniqueConstraint("contact_id", "channel_type", "value", name="uq_contact_channel"),
        CheckConstraint("channel_type IN ('line_user_id', 'line_group_id', 'email', 'phone')", name="ck_channel_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contact.id"), index=True)
    channel_type: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(255), index=True)
    contact: Mapped[Contact] = relationship(back_populates="channels")
