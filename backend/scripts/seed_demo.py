"""Idempotent local/demo dataset for ISMS. Never runs at application startup.

    python scripts/seed_demo.py --apply            # reference data + demo accounts
    python scripts/seed_demo.py --apply --cases    # also create sample cases through the API

What it creates (only when missing, matched by natural keys):
- Products ExamPlus / GetA / Logbook with modules and the three category axes
  from SRS appendix B, standard cause/solution codes, case templates and
  canned replies.
- Support teams per tier with routes for every product, team leads, and one
  demo account per role. Password: env ISMS_DEMO_PASSWORD (default
  "Demo@123456", local only).
- Fixed-date Thai public holidays for 2026-2027 on "Thailand Business
  Calendar". Lunar holidays (Makha/Visakha/Asarnha Bucha) vary each year and
  must be added by Admin from the official announcement.
- Customer organizations labelled "(DEMO)" with departments, courses/exams,
  contacts, product instances and one exam window that is active now.

Refuses to run when APP_ENV=production. Existing rows are never modified,
except that a missing product SLA policy/default team is filled in.
"""
import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: F401  (registers every model and router)
from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.models.customer import ChannelIdentity, Contact, Organization
from app.db.models.customer_context import CourseOrExam, Department, ExamWindow
from app.db.models.master_data import (
    BusinessCalendar, BusinessHoliday, CannedMessage, CaseTemplate, CauseCode, Module,
    ProblemType, Product, ServiceStage, SlaPolicy, SolutionCode, Symptom,
)
from app.db.models.product import ProductInstance
from app.db.models.routing import ProductTierRoute, RoutingPolicy, TeamRouting
from app.db.models.user import Role, Team, User
from app.db.session import SessionLocal

PRODUCTS = {
    "examplus": ("ExamPlus", "ระบบจัดสอบออนไลน์", {
        "Teacher": ("teacher", ["สร้าง/ตั้งค่าข้อสอบ", "ตรวจและประกาศคะแนน", "จัดการกลุ่มผู้สอบ"]),
        "Proctor": ("proctor", ["เปิด/คุมห้องสอบ", "ยืนยันตัวตนผู้สอบ"]),
        "Student (Web)": ("student-web", ["เข้าสอบไม่ได้", "ส่งคำตอบไม่สำเร็จ"]),
        "Student (App)": ("student-app", ["ดาวน์โหลดข้อสอบไม่ได้", "แอปค้างระหว่างสอบ"]),
    }),
    "geta": ("GetA", "ระบบประเมินผลการเรียนรู้", {
        "Teacher": ("teacher", ["สร้างแบบประเมิน", "ดูรายงานผล"]),
        "Student": ("student", ["ส่งงานไม่สำเร็จ", "มองไม่เห็นแบบประเมิน"]),
        "Admin": ("admin", ["นำเข้ารายชื่อ", "สิทธิ์ผู้ใช้"]),
    }),
    "logbook": ("Logbook", "สมุดบันทึกหัตถการและแฟ้มสะสมงานคลินิก", {
        "Clinical Procedures": ("clinical", ["บันทึกหัตถการไม่สำเร็จ", "ข้อมูลหัตถการผิด"]),
        "Supervisor Verification": ("supervisor", ["อาจารย์รับรองไม่ได้", "การแจ้งเตือนไม่ถึงอาจารย์"]),
        "Portfolio": ("portfolio", ["ส่งออกแฟ้มสะสมงาน"]),
    }),
}
SYMPTOMS = ["ดาวน์โหลด/อัปโหลดล้มเหลว", "บัญชีผู้ใช้/กลุ่ม", "สิทธิ์การเข้าถึง", "ตั้งค่าไม่ถูกต้อง",
            "ข้อมูล/เนื้อหาผิด", "แม่แบบ (Template)", "อุปกรณ์/แพลตฟอร์ม", "เครือข่าย/สภาพแวดล้อม"]
STAGES = ["ก่อนสอบ", "ระหว่างสอบ", "หลังสอบ", "ทั่วไป"]
CAUSES = [("CFG", "ตั้งค่าระบบไม่ครบหรือไม่ถูกต้อง"), ("USR", "ผู้ใช้ใช้งานผิดขั้นตอน"),
          ("NET", "เครือข่ายของผู้ใช้ขัดข้อง"), ("DATA", "ข้อมูลต้นทางไม่ถูกต้อง"),
          ("BUG", "ข้อบกพร่องของระบบ"), ("DEV", "อุปกรณ์หรือเบราว์เซอร์ไม่รองรับ")]
SOLUTIONS = [("GUIDE", "แนะนำขั้นตอนการใช้งาน"), ("RECONFIG", "ปรับการตั้งค่าและทดสอบซ้ำ"),
             ("FIXDATA", "แก้ไขข้อมูลในระบบ"), ("ACCESS", "เพิ่มหรือปรับสิทธิ์ผู้ใช้"),
             ("PATCH", "แก้ไขโดยทีมพัฒนา"), ("WORKAROUND", "ใช้วิธีเลี่ยงชั่วคราว")]
TEAMS = [("ทีมซัพพอร์ต", "Tier 2 รับเรื่องและแก้ปัญหาพื้นฐาน", 2),
         ("ทีมผู้เชี่ยวชาญ", "Tier 1 วิเคราะห์ปัญหาเชิงลึก", 1),
         ("ทีมพัฒนา", "Tier 0 แก้ไขระบบ", 0)]
ACCOUNTS = [  # username, full name, role, team index, tier, leads team
    ("lead", "หัวหน้าทีมซัพพอร์ต (Demo)", "Team Lead", 0, 2, True),
    ("agent1", "เจ้าหน้าที่ซัพพอร์ต 1 (Demo)", "Agent", 0, 2, False),
    ("agent2", "เจ้าหน้าที่ซัพพอร์ต 2 (Demo)", "Agent", 0, 2, False),
    ("specialist", "ผู้เชี่ยวชาญระบบ (Demo)", "Specialist", 1, 1, True),
    ("developer", "นักพัฒนา (Demo)", "Developer", 2, 0, True),
    ("executive", "ผู้บริหาร (Demo)", "Executive", None, None, False),
]
FIXED_HOLIDAYS = [((1, 1), "วันขึ้นปีใหม่"), ((4, 6), "วันจักรี"), ((4, 13), "วันสงกรานต์"),
                  ((4, 14), "วันสงกรานต์"), ((4, 15), "วันสงกรานต์"), ((5, 1), "วันแรงงานแห่งชาติ"),
                  ((5, 4), "วันฉัตรมงคล"), ((6, 3), "วันเฉลิมพระชนมพรรษาพระราชินี"),
                  ((7, 28), "วันเฉลิมพระชนมพรรษา ร.10"), ((8, 12), "วันแม่แห่งชาติ"),
                  ((10, 13), "วันนวมินทรมหาราช"), ((10, 23), "วันปิยมหาราช"),
                  ((12, 5), "วันพ่อแห่งชาติ"), ((12, 10), "วันรัฐธรรมนูญ"), ((12, 31), "วันสิ้นปี")]
CUSTOMERS = [
    ("มหาวิทยาลัยตัวอย่าง (DEMO)", ["คณะแพทยศาสตร์", "คณะเภสัชศาสตร์"],
     [("วิชาเวชศาสตร์ครอบครัว", "course"), ("MEQ ปลายภาค", "exam")],
     [("อ.นนท์ ใจดี", "nont@demo.example"), ("คุณฝน ศูนย์สอบ", "fon@demo.example")],
     ["examplus", "geta"], True),
    ("โรงพยาบาลตัวอย่าง (DEMO)", ["แผนกฝึกอบรมแพทย์"], [("Clinical rotation", "course")],
     [("พญ.มิ้นท์ ศึกษา", "mint@demo.example")], ["logbook"], False),
    ("สภาวิชาชีพตัวอย่าง (DEMO)", [], [("สอบใบอนุญาต รอบพิเศษ", "exam")],
     [("คุณบอส ทะเบียน", "boss@demo.example")], ["examplus", "logbook"], False),
]
TEMPLATES = [("ดาวน์โหลดข้อสอบไม่ได้", "examplus", "Student (App)", "ดาวน์โหลดข้อสอบไม่ได้", "S2"),
             ("ขอเพิ่มสิทธิ์อาจารย์", "geta", "Admin", "สิทธิ์ผู้ใช้", "S4")]
CANNED = [("รับเรื่องแล้ว", "ได้รับเรื่องแล้วค่ะ ทีมงานกำลังตรวจสอบ จะแจ้งความคืบหน้าภายในเวลาที่กำหนด"),
          ("ขอข้อมูลเพิ่ม", "รบกวนส่งภาพหน้าจอ เวลาที่พบปัญหา และชื่อรายวิชา/ห้องสอบ เพื่อให้ตรวจสอบได้เร็วขึ้นค่ะ"),
          ("แก้ไขแล้ว", "ดำเนินการแก้ไขเรียบร้อยแล้ว รบกวนทดลองใช้งานอีกครั้ง หากยังพบปัญหาแจ้งกลับได้ภายใน 14 วันค่ะ")]


class Seeder:
    def __init__(self, db):
        self.db, self.created = db, 0

    def ensure(self, model, keys, **values):
        row = self.db.scalar(select(model).filter_by(**keys))
        if row is None:
            row = model(**keys, **values)
            self.db.add(row)
            self.db.flush()
            self.created += 1
        return row

    def run(self, password):
        db = self.db
        policy = db.scalar(select(SlaPolicy).where(SlaPolicy.name == "Default SLA Policy"))
        calendar = db.scalar(select(BusinessCalendar).where(BusinessCalendar.name == "Thailand Business Calendar"))
        if policy is None or calendar is None:
            raise RuntimeError("Start the API once (init_db) before seeding demo data")
        for year in (2026, 2027):
            for (month, day), name in FIXED_HOLIDAYS:
                self.ensure(BusinessHoliday, {"business_calendar_id": calendar.id,
                                              "holiday_date": date(year, month, day)}, name=name)
        policy_row = self.ensure(RoutingPolicy, {"id": 1}, s1_minutes=15, enabled=True)
        if policy_row.business_calendar_id is None:
            policy_row.business_calendar_id = calendar.id

        teams = [self.ensure(Team, {"name": name}, description=description) for name, description, _ in TEAMS]
        roles = {role.name: role for role in db.scalars(select(Role))}
        users = {}
        for username, full_name, role, team_index, tier, leads in ACCOUNTS:
            users[username] = self.ensure(
                User, {"username": username}, email=f"{username}@isms.local", full_name=full_name,
                hashed_password=get_password_hash(password), role_id=roles[role].id, is_active=True,
                team_id=teams[team_index].id if team_index is not None else None,
                default_tier=tier if tier is not None else 2, is_available=True)
            if leads:
                self.ensure(TeamRouting, {"team_id": teams[team_index].id}, leader_id=users[username].id)

        for code, solution in CAUSES:
            self.ensure(CauseCode, {"code": code}, name=solution)
        for code, solution in SOLUTIONS:
            self.ensure(SolutionCode, {"code": code}, name=solution)
        catalogue = {}
        for code, (name, description, modules) in PRODUCTS.items():
            product = self.ensure(Product, {"code": code}, name=name, description=description)
            product.sla_policy_id = product.sla_policy_id or policy.id
            product.default_team_id = product.default_team_id or teams[0].id
            for (_, _, tier), team in zip(TEAMS, teams):
                self.ensure(ProductTierRoute, {"product_id": product.id, "tier": tier}, team_id=team.id)
            for symptom in SYMPTOMS:
                self.ensure(Symptom, {"product_id": product.id, "name": symptom})
            for order, stage in enumerate(STAGES):
                self.ensure(ServiceStage, {"product_id": product.id, "name": stage}, sort_order=order)
            catalogue[code] = {"product": product, "modules": {}}
            for module_name, (module_code, problems) in modules.items():
                module = self.ensure(Module, {"product_id": product.id, "name": module_name}, code=module_code)
                catalogue[code]["modules"][module_name] = (module, {
                    problem: self.ensure(ProblemType, {"module_id": module.id, "name": problem})
                    for problem in problems})
        for name, product_code, module_name, problem, severity in TEMPLATES:
            module, problems = catalogue[product_code]["modules"][module_name]
            self.ensure(CaseTemplate, {"name": name}, product_id=catalogue[product_code]["product"].id,
                        module_id=module.id, problem_type_id=problems[problem].id, default_severity=severity)
        for name, message in CANNED:
            self.ensure(CannedMessage, {"name": name}, message=message)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for org_name, departments, courses, contacts, products, exam_now in CUSTOMERS:
            org = self.ensure(Organization, {"name": org_name}, is_active=True)
            for department in departments:
                self.ensure(Department, {"organization_id": org.id, "name": department},
                            name_key=department.casefold())
            for course, kind in courses:
                self.ensure(CourseOrExam, {"organization_id": org.id, "name": course, "kind": kind},
                            name_key=course.casefold())
            for contact_name, email in contacts:
                contact = self.ensure(Contact, {"organization_id": org.id, "name": contact_name})
                self.ensure(ChannelIdentity, {"contact_id": contact.id, "channel_type": "email", "value": email})
            for product_code in products:
                product = catalogue[product_code]["product"]
                self.ensure(ProductInstance, {"organization_id": org.id, "product_id": product.id,
                                              "code": "production"},
                            name=f"{product.name} · {org_name.split(' ')[0]}", version="2.4",
                            environment="production", url=f"https://{product_code}.demo.example")
            if exam_now:
                start = datetime.combine(now.date(), time(0))
                self.ensure(ExamWindow, {"organization_id": org.id, "name": "สอบปลายภาค (DEMO)"},
                            starts_at=start - timedelta(days=1), ends_at=start + timedelta(days=6))
        return users


def create_cases(password):
    """Create a few realistic cases through the real API, so numbering, SLA,
    routing and audit behave exactly as in production."""
    from fastapi.testclient import TestClient

    client = TestClient(app.main.app)
    token = client.post("/api/v1/auth/login", data={"username": "agent1", "password": password}).json()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.name == CUSTOMERS[0][0]))
        contact = db.scalar(select(Contact).where(Contact.organization_id == org.id))
        instance = db.scalar(select(ProductInstance).where(ProductInstance.organization_id == org.id))
    samples = [("ดาวน์โหลดข้อสอบไม่ได้ทั้งห้องสอบ", "line_group", "organization"),
               ("กดเริ่มสอบ MEQ แล้วขึ้นว่าหมดเวลา", "line_oa", "group"),
               ("ขอเพิ่มสิทธิ์อาจารย์เข้ากลุ่มรายวิชา", "phone", "non_disruptive")]
    made = 0
    for subject, channel, impact in samples:
        body = {"organization_id": org.id, "contact_id": contact.id, "subject": subject, "channel": channel,
                "product_instance_id": instance.id, "impact_scope": impact}
        similar = client.get("/api/v1/tickets/similar", headers=headers, params={
            "q": subject, "organization_id": org.id, "product_instance_id": instance.id}).json()
        if similar.get("decision_required"):
            client.post(f"/api/v1/tickets/similarity-feedback/{similar['feedback_id']}",
                        headers=headers, json={"decision": "new"})
            body["similarity_feedback_id"] = similar["feedback_id"]
        response = client.post("/api/v1/tickets", headers=headers, json=body)
        if response.status_code != 201:
            raise RuntimeError(f"Sample case failed: {response.status_code} {response.text}")
        made += 1
    return made


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="save the demo dataset")
    parser.add_argument("--cases", action="store_true", help="also create sample cases via the API")
    args = parser.parse_args()
    if not args.apply:
        parser.error("Pass --apply to create the demo dataset")
    if os.getenv("APP_ENV", "local").lower() in {"production", "prod"}:
        sys.exit("Refusing to seed demo data in production")
    password = os.getenv("ISMS_DEMO_PASSWORD", "Demo@123456")
    with SessionLocal() as db:
        try:
            seeder = Seeder(db)
            seeder.run(password)
            db.commit()
        except Exception:
            db.rollback()
            raise
    print(f"Demo reference data ready ({seeder.created} new rows).")
    if args.cases:
        print(f"Created {create_cases(password)} sample cases.")
