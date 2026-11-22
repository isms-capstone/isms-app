"""Bulk-insert synthetic cases into a disposable database for load testing.

    MARIADB_DB=isms_perf_qa python scripts/perf_seed_cases.py 50000

Refuses any database whose name does not end with "_qa". Rows bypass the API
on purpose (speed); they are realistic enough for list/queue timing only.
"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: F401
from sqlalchemy import insert, select

from app.core.config import settings
from app.db.models.customer import Organization
from app.db.models.product import ProductInstance
from app.db.models.ticket import Ticket
from app.db.models.user import User
from app.db.session import SessionLocal

if not settings.MARIADB_DB.endswith("_qa"):
    sys.exit("Refusing to bulk insert outside a *_qa database")
count = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
rng = random.Random(42)
now = datetime.now(timezone.utc).replace(tzinfo=None)
statuses = ["NEW", "IN_PROGRESS", "PENDING_CUSTOMER", "PENDING_EXTERNAL", "RESOLVED", "CLOSED", "CLOSED", "CLOSED"]
channels = ["line_oa", "line_group", "line_personal", "phone", "portal", "email"]
words = ["ดาวน์โหลดข้อสอบไม่ได้", "เข้าระบบไม่ได้", "ส่งคำตอบไม่สำเร็จ", "ขอเพิ่มสิทธิ์อาจารย์",
         "คะแนนแสดงผิด", "ขอ Export ข้อมูล", "แอปค้างระหว่างสอบ", "รีเซ็ตรหัสผ่าน"]
with SessionLocal() as db:
    orgs = db.scalars(select(Organization.id)).all()
    instances = db.execute(select(ProductInstance.id, ProductInstance.organization_id)).all()
    users = db.scalars(select(User.id)).all()
    admin = users[0]
    batch = []
    for index in range(count):
        instance_id, org_id = rng.choice(instances)
        created = now - timedelta(minutes=rng.randint(0, 60 * 24 * 365))
        status = rng.choice(statuses)
        open_case = status not in {"RESOLVED", "CLOSED"}
        due = created + timedelta(hours=rng.randint(1, 72)) if open_case and status != "PENDING_CUSTOMER" else None
        batch.append(dict(
            ticket_no=f"PERF-{created:%Y%m}-{index:07d}", subject=f"{rng.choice(words)} #{index}",
            status=status, channel=rng.choice(channels), organization_id=org_id,
            product_instance_id=instance_id, severity=rng.choice(["S1", "S2", "S3", "S3", "S4"]),
            current_tier=rng.choice([2, 2, 2, 1, 0]), created_by_id=admin,
            assignee_id=rng.choice(users + [None, None]), created_at=created, reported_at=created,
            sla_due_at=due, sla_risk_at=due - timedelta(minutes=30) if due else None,
            sla_breached=bool(due and due < now and rng.random() < 0.3), reopen_count=0,
            is_exam_window=False, routing_version=0))
        if len(batch) == 2000:
            db.execute(insert(Ticket), batch)
            db.commit()
            batch.clear()
    if batch:
        db.execute(insert(Ticket), batch)
        db.commit()
print(f"Inserted {count} synthetic cases")
