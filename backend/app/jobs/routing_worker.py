"""Run with python -m app.jobs.routing_worker. Five-minute cadence, separate from web processes."""

import logging
import signal
from threading import Event

from app.db.migration_state import require_current_schema
from app.db.session import SessionLocal, engine
from app.services.routing_jobs import run_routing_checks

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
        stop.wait(300)


if __name__ == "__main__":
    main()
