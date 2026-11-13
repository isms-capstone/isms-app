"""Allow-listed customer payloads over the canonical WRK storage."""

from sqlalchemy import and_, or_, select

from app.db.models.work_category import TicketWorklog

EXTERNAL_CHANNELS = {
    "portal": ("portal",),
    "email": ("email",),
    "line": ("line_oa", "line_group", "line_personal"),
}


def external_replies(db, ticket_id: int, channel: str):
    if channel not in EXTERNAL_CHANNELS:
        raise ValueError("Unsupported external channel")
    rows = db.scalars(
        select(TicketWorklog)
        .where(
            or_(
                TicketWorklog.original_ticket_id == ticket_id,
                and_(TicketWorklog.original_ticket_id.is_(None), TicketWorklog.ticket_id == ticket_id),
            ),
            TicketWorklog.is_internal.is_(False),
            TicketWorklog.channel.in_(EXTERNAL_CHANNELS[channel]),
        )
        .order_by(TicketWorklog.created_at, TicketWorklog.id)
    ).all()
    return [
        {
            "id": row.id,
            "body": row.body,
            "channel": row.channel,
            "created_at": row.created_at.isoformat() + "Z",
        }
        for row in rows
    ]
