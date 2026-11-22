"""SEA persistence for searchable terms, saved views and export records."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class CaseSearchToken(Base):
    __tablename__ = 'case_search_token'
    __table_args__ = (Index('ix_case_search_token_lookup', 'token', 'ticket_id'),)

    ticket_id: Mapped[int] = mapped_column(ForeignKey('ticket.id'), primary_key=True)
    # 0 is the case itself. A positive value is a worklog ID.
    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(
        String(191).with_variant(VARCHAR(191, charset='utf8mb4', collation='utf8mb4_bin'), 'mysql', 'mariadb'),
        primary_key=True,
    )


class CaseSearchView(Base):
    __tablename__ = 'case_search_view'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), index=True)
    filters: Mapped[dict] = mapped_column(JSON)


class CaseExportAudit(Base):
    __tablename__ = 'case_export_audit'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    format: Mapped[str] = mapped_column(String(4))
    filters: Mapped[dict] = mapped_column(JSON)
    ticket_ids: Mapped[list[int]] = mapped_column(JSON)
