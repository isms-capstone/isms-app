from datetime import time

from sqlalchemy.orm import Session

from app.db.base_class import Base
from app.db.session import engine, SessionLocal
from app.db.models.user import Role, User, Team
from app.db.models.master_data import (
    TicketType,
    SlaPolicy,
    SlaPolicyRule,
    BusinessCalendar,
)
from app.core.security import get_password_hash


DEFAULT_TICKET_TYPES = [
    "Issues",
    "Bugs",
    "Request",
    "Question",
    "Export Data",
    "Data Transfer",
    "Data Recovery",
    "Change Request",
]



DEFAULT_SLA_POLICY = {
    "name": "Default SLA Policy",
    "description": "บริษัทใช้เป็นค่าเริ่มต้นสำหรับทุกลูกค้า",
}

DEFAULT_SLA_RULES = [
    {
        "severity": "S1",
        "first_response_value": 15,
        "first_response_unit": "MINUTES",
        "resolution_min_value": 5,
        "resolution_max_value": 5,
        "resolution_unit": "HOURS",
        "business_hours_only": False,
    },
    {
        "severity": "S2",
        "first_response_value": 30,
        "first_response_unit": "MINUTES",
        "resolution_min_value": 1,
        "resolution_max_value": 1,
        "resolution_unit": "BUSINESS_DAYS",
        "business_hours_only": True,
    },
    {
        "severity": "S3",
        "first_response_value": 4,
        "first_response_unit": "HOURS",
        "resolution_min_value": 1,
        "resolution_max_value": 3,
        "resolution_unit": "BUSINESS_DAYS",
        "business_hours_only": True,
    },
    {
        "severity": "S4",
        "first_response_value": 1,
        "first_response_unit": "BUSINESS_DAYS",
        "resolution_min_value": 5,
        "resolution_max_value": 10,
        "resolution_unit": "BUSINESS_DAYS",
        "business_hours_only": True,
    },
]

DEFAULT_BUSINESS_CALENDAR = {
    "name": "Thailand Business Calendar",
    "description": "วันทำการมาตรฐานของบริษัท",
    "timezone": "Asia/Bangkok",
    "work_start_time": time(8, 0),
    "work_end_time": time(17, 0),
    "monday": True,
    "tuesday": True,
    "wednesday": True,
    "thursday": True,
    "friday": True,
    "saturday": False,
    "sunday": False,
}


SYSTEM_ROLES = [
    {"name": "Admin", "description": "System administrator; manages users, teams, roles and settings."},
    {"name": "Agent", "description": "Tier 2 support agent; receives cases from all channels."},
    {"name": "Specialist", "description": "Tier 1 specialist; receives escalated cases from Agent."},
    {"name": "Developer", "description": "Tier 0 developer; investigates and resolves escalated cases."},
    {"name": "Team Lead", "description": "Support team lead; manages workload distribution and SLA."},
    {"name": "Executive", "description": "Executive; views high-level dashboards."},
]


def init_db(db: Session) -> None:
    Base.metadata.create_all(bind=engine)

    # Seed by unique role name, never assume that a role has a specific primary key.
    for role_data in SYSTEM_ROLES:
        role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if role is None:
            db.add(Role(**role_data))

    teams_data = [
        {"name": "IT & Security", "description": "Core IT Security Team"},
        {"name": "Compliance & Audit", "description": "Internal Audit Team"},
    ]
    for team_data in teams_data:
        if not db.query(Team).filter(Team.name == team_data["name"]).first():
            db.add(Team(**team_data))
    db.commit()

    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    agent_role = db.query(Role).filter(Role.name == "Agent").first()
    executive_role = db.query(Role).filter(Role.name == "Executive").first()
    it_team = db.query(Team).filter(Team.name == "IT & Security").first()

    # Existing demo accounts are created only when absent. Never reset passwords on startup.
    demo_users = [
        {
            "username": "admin",
            "email": "admin@isms.local",
            "full_name": "System Administrator",
            "password": "Admin@123456",
            "role_id": admin_role.id,
            "team_id": it_team.id if it_team else None,
        },
        {
            "username": "mimi",
            "email": "mimi@isms.local",
            "full_name": "Mimi (Legacy Demo Account)",
            "password": "User@123456",
            "role_id": agent_role.id,
            "team_id": it_team.id if it_team else None,
        },
        {
            "username": "mai",
            "email": "mai@isms.local",
            "full_name": "Mai (Legacy Demo Account)",
            "password": "Auditor@123456",
            "role_id": executive_role.id,
            "team_id": None,
        },
    ]
    for data in demo_users:
        existing = db.query(User).filter(User.username == data["username"]).first()
        if existing is None:
            data = data.copy()
            password = data.pop("password")
            db.add(User(
                **data,
                hashed_password=get_password_hash(password),
                is_active=True,
            ))
    # ADM-04: seed one default SLA policy, its S1-S4 rules, and the standard
    # Thailand business calendar. All seeds are idempotent so startup never duplicates them.
    sla_policy = db.query(SlaPolicy).filter(SlaPolicy.name == DEFAULT_SLA_POLICY["name"]).first()
    if sla_policy is None:
        sla_policy = SlaPolicy(**DEFAULT_SLA_POLICY)
        db.add(sla_policy)
        db.flush()

    for rule_data in DEFAULT_SLA_RULES:
        exists = db.query(SlaPolicyRule).filter(
            SlaPolicyRule.sla_policy_id == sla_policy.id,
            SlaPolicyRule.severity == rule_data["severity"],
        ).first()
        if exists is None:
            db.add(SlaPolicyRule(sla_policy_id=sla_policy.id, **rule_data))

    calendar = db.query(BusinessCalendar).filter(BusinessCalendar.name == DEFAULT_BUSINESS_CALENDAR["name"]).first()
    if calendar is None:
        db.add(BusinessCalendar(**DEFAULT_BUSINESS_CALENDAR))

    # CAT-02: seed the organisation's standard ticket types idempotently.
    # Admin can add/remove values later through the master-data API.
    for ticket_type_name in DEFAULT_TICKET_TYPES:
        if not db.query(TicketType).filter(TicketType.name == ticket_type_name).first():
            db.add(TicketType(name=ticket_type_name))
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
