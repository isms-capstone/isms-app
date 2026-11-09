"""Ephemeral QA server; isolated temporary fixtures, actual login and RBAC."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.api.v1.endpoints import tickets
from app.api.v1.router import api_router
from app.core.security import get_password_hash
from app.db.base_class import Base
from app.db.models.user import Role, Team, User
from app.db.session import get_db
from app.registry_ui import mount_registry_ui

temporary_db = TemporaryDirectory(prefix="isms-registry-qa-")
tickets.ATTACHMENT_DIR = Path(temporary_db.name) / "attachments"

external_qa = os.getenv("REGISTRY_BROWSER_MARIADB_QA") == "1"
if external_qa:
    from app.core.config import settings
    from app.db.migration_state import require_current_schema
    from app.db.session import engine

    if not settings.MARIADB_DB.endswith("_browser_qa"):
        raise RuntimeError(
            "Browser MariaDB fixtures require a dedicated *_browser_qa database"
        )
    with engine.connect() as connection:
        require_current_schema(connection)
else:
    database_path = (Path(temporary_db.name) / "registry.sqlite").as_posix()
    engine = create_engine(
        f"sqlite:///{database_path}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine, expire_on_commit=False)
with factory() as db:
    db.add_all(
        [
            Role(id=20, name="Admin"),
            Role(id=21, name="Agent"),
            Role(id=22, name="Auditor"),
            Team(name="Support"),
        ]
    )
    db.flush()
    hashed = get_password_hash("test-only-password")
    for username, role_id in [("qa-admin", 20), ("qa-agent", 21), ("qa-auditor", 22)]:
        db.add(
            User(
                username=username,
                email=f"{username}@example.org",
                role_id=role_id,
                hashed_password=hashed,
                is_active=True,
            )
        )
    db.commit()
app = FastAPI()
app.include_router(api_router, prefix="/api/v1")
mount_registry_ui(app)


def database():
    with factory() as db:
        yield db


app.dependency_overrides[get_db] = database


# ESC browser fixtures live only in this temporary QA database.
from datetime import UTC, datetime, timedelta

from app.db.models.customer import Organization
from app.db.models.master_data import Product
from app.db.models.product import ProductInstance
from app.db.models.routing import ProductTierRoute, RoutingNotification, TeamRouting
from app.db.models.ticket import Ticket
from app.services.routing import initialize_interval
from sqlalchemy import select

with factory() as db:
    support = db.scalar(select(Team).where(Team.name == "Support"))
    specialist_team = Team(name="QA Specialists")
    dev_team = Team(name="QA Developers")
    db.add_all([specialist_team, dev_team])
    db.flush()
    for username in ("qa-admin", "qa-agent"):
        db.scalar(select(User).where(User.username == username)).team_id = support.id
    specialist_role = Role(name="Specialist")
    dev_role = Role(name="Developer")
    db.add_all([specialist_role, dev_role])
    db.flush()
    for name, role, tier, team in [
        ("qa-peer", 21, 2, support.id),
        ("qa-specialist", specialist_role.id, 1, specialist_team.id),
        ("qa-developer", dev_role.id, 0, dev_team.id),
    ]:
        db.add(
            User(
                username=name,
                email=f"{name}@example.org",
                role_id=role,
                team_id=team,
                default_tier=tier,
                hashed_password=hashed,
                is_active=True,
            )
        )
    db.flush()
    admin = db.scalar(select(User).where(User.username == "qa-admin"))
    agent = db.scalar(select(User).where(User.username == "qa-agent"))
    org = Organization(name="ESC QA customer")
    db.add(org)
    db.flush()
    product = Product(code="ESC-QA", name="ESC QA Product", default_team_id=support.id)
    db.add(product)
    db.flush()
    instance = ProductInstance(
        organization_id=org.id,
        product_id=product.id,
        code="qa",
        name="ESC QA instance",
        version="1",
        environment="test",
        url="https://example.org",
    )
    db.add(instance)
    db.flush()
    for tier, team in [(2, support.id), (1, specialist_team.id), (0, dev_team.id)]:
        db.add(ProductTierRoute(product_id=product.id, tier=tier, team_id=team))
    db.add(TeamRouting(team_id=support.id, leader_id=admin.id))
    now = datetime.now(UTC).replace(tzinfo=None)
    for suffix, assignee in [
        ("HANDOFF", agent.id),
        ("PICKUP", None),
        ("BULK", agent.id),
    ]:
        case = Ticket(
            ticket_no=f"ESC-QA-{suffix}",
            subject=f"ESC {suffix} acceptance",
            status="NEW",
            channel="phone",
            organization_id=org.id,
            product_instance_id=instance.id,
            owner_id=agent.id,
            assignee_id=assignee,
            created_by_id=agent.id,
            current_tier=2,
            reported_at=now,
            created_at=now - timedelta(minutes=20),
            severity="S2",
        )
        db.add(case)
        db.flush()
        initialize_interval(db, case, case.created_at)
        if suffix == "HANDOFF":
            db.add(
                RoutingNotification(
                    recipient_id=admin.id,
                    ticket_id=case.id,
                    dedupe_key="qa-stalled",
                    kind="new_stalled",
                    message="ESC-QA-HANDOFF: NEW ค้างเกิน 15 นาที",
                    created_at=now,
                )
            )
    db.commit()

# Prepared inputs only: the browser performs all routing actions through real forms.
from datetime import time

from app.db.models.master_data import (
    BusinessCalendar,
    CauseCode,
    Module,
    ProblemType,
    SolutionCode,
)
from app.db.models.routing import RoutingPolicy

with factory() as db:
    agent_role = db.scalar(select(Role).where(Role.name == "Agent"))
    auto_user = User(
        username="qa-auto",
        email="qa-auto@example.org",
        role_id=agent_role.id,
        hashed_password=hashed,
        team_id=support.id,
        default_tier=2,
        is_active=True,
    )
    db.add(auto_user)
    db.flush()
    module = Module(product_id=product.id, code="esc-audit", name="QA ESC module")
    db.add(module)
    db.flush()
    db.add(ProblemType(module_id=module.id, name="QA ESC issue"))
    db.add(CauseCode(code="ESC-QA", name="QA cause"))
    db.add(SolutionCode(code="ESC-QA", name="QA solution"))
    calendar = BusinessCalendar(
        name="ESC QA all-day",
        work_start_time=time(0),
        work_end_time=time(23, 59, 59),
        monday=True,
        tuesday=True,
        wednesday=True,
        thursday=True,
        friday=True,
        saturday=True,
        sunday=True,
    )
    db.add(calendar)
    db.flush()
    policy = db.get(RoutingPolicy, 1)
    if policy is None:
        policy = RoutingPolicy(id=1)
        db.add(policy)
    policy.enabled = not external_qa
    policy.s1_minutes = 15
    policy.business_calendar_id = calendar.id
    for suffix, severity, assigned in [
        ("CHAIN", "S2", True),
        ("ASSIGN", "S3", False),
        ("S1", "S1", True),
        ("ACK", "S1", True),
        ("STALLED", "S3", True),
    ]:
        case = Ticket(
            ticket_no=f"ESC-AUDIT-{suffix}",
            subject=f"ESC audit {suffix}",
            status="NEW",
            channel="phone",
            organization_id=org.id,
            product_instance_id=instance.id,
            module_id=module.id,
            owner_id=auto_user.id,
            assignee_id=auto_user.id if assigned else None,
            created_by_id=auto_user.id,
            current_tier=2,
            reported_at=now,
            created_at=now - timedelta(minutes=20),
            severity=severity,
        )
        db.add(case)
        db.flush()
        initialize_interval(db, case, case.created_at)
    db.commit()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
