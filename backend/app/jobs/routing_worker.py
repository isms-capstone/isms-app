"""Run with python -m app.jobs.routing_worker. Five-minute cadence, separate from web processes."""

import logging
import signal
from threading import Event

from app.db.migration_state import require_current_schema

# A standalone worker does not import the HTTP router that normally registers
# these tables. Ticket flushes must still resolve every customer-context FK.
from app.db.models import customer, customer_context  # noqa: F401
from app.db.session import SessionLocal, engine
from app.services.routing_jobs import run_routing_checks
from app.services.sla_engine import run_sla_checks

logger = logging.getLogger(__name__)


def backfill_teams(db, batch=500):
    """Give open cases created before ADM-06 their responsible team."""
    from sqlalchemy import select

    from app.db.models.ticket import OPEN_STATUSES, Ticket
    from app.services.routing import assign_responsible_team

    for ticket in db.scalars(select(Ticket).where(Ticket.team_id.is_(None), Ticket.status.in_(OPEN_STATUSES))
                             .limit(batch)):
        assign_responsible_team(db, ticket)
    db.commit()


def main():
    logging.basicConfig(level=logging.INFO)
    stop = Event()
    for name in ("SIGINT", "SIGTERM"):
        signal.signal(getattr(signal, name), lambda *_: stop.set())
    with engine.connect() as connection:
        require_current_schema(connection)
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                logger.info("Routing checks: %s", run_routing_checks(db))
        except Exception:
            logger.exception("Routing checks failed; transaction rolled back")
        try:
            with SessionLocal() as db:
                logger.info("SLA notifications: %s", run_sla_checks(db))
        except Exception:
            logger.exception("SLA checks failed")
        try:
            with SessionLocal() as db:
                backfill_teams(db)
        except Exception:
            logger.exception("Team backfill failed")
        try:
            from app.services.auto_close import run_auto_close_resolved_tickets
            with SessionLocal() as db:
                logger.info("Cases closed automatically: %s", run_auto_close_resolved_tickets(db))
        except Exception:
            logger.exception("Automatic closure failed")
        try:
            from app.services.portal_access import purge_expired_links
            from app.services.portal_mail import deliver_replies
            with SessionLocal() as db:
                logger.info("Portal e-mails sent: %s", deliver_replies(db))
                purge_expired_links(db)
        except Exception:
            logger.exception("Portal email delivery failed")
        stop.wait(300)


if __name__ == "__main__":
    main()
