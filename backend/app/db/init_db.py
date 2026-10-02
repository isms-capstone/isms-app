from sqlalchemy.orm import Session

from app.db.base_class import Base
from app.db.session import engine, SessionLocal
from app.db.models.user import Role, User, Team
from app.core.security import get_password_hash


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
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
