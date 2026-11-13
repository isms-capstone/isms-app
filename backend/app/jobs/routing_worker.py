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
        stop.wait(300)


if __name__ == "__main__":
    main()
