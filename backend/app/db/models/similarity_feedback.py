"""Every time SIM proposes results, record what was proposed and what the user chose (SIM-09 / KPI-10)."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class SimilarityFeedback(Base):
    __tablename__ = 'similarity_feedback'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int | None] = mapped_column(
    ForeignKey('ticket.id'),
    index=True,
    nullable=True,
)
    # [{"ticket_id": 12, "score": 85}, ...]
    suggested: Mapped[list] = mapped_column(JSON, default=list)
    # 'reuse' (ใช้วิธีแก้เดิม) | 'link' (ผูกกับรายการเดิม) | 'new' (เปิดสอบสวนใหม่)
    decision: Mapped[str | None] = mapped_column(String(16))
    chosen_ticket_id: Mapped[int | None] = mapped_column(ForeignKey('ticket.id'))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
