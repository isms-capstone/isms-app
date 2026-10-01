from sqlalchemy.orm import Session
from app.db.base_class import Base
from app.db.session import engine, SessionLocal
from app.db.models.user import Role, User, Team
from app.core.security import get_password_hash

def init_db(db: Session) -> None:
    Base.metadata.create_all(bind=engine)

    # 1. Seed Roles
    roles_data = [
        {"id": 4, "name": "Admin", "description": "System Administrator with full access"},
        {"id": 5, "name": "User", "description": "Standard User"},
        {"id": 6, "name": "Auditor", "description": "Read-only Auditor for ISMS Compliance"},
    ]
    for r_data in roles_data:
        role = db.get(Role, r_data["id"])
        if not role:
            db.add(Role(**r_data))
    db.commit()

    # 2. Seed Teams
    teams_data = [
        {"name": "IT & Security", "description": "Core IT Security Team"},
        {"name": "Compliance & Audit", "description": "Internal Audit Team"},
    ]
    for t_data in teams_data:
        team = db.query(Team).filter(Team.name == t_data["name"]).first()
        if not team:
            db.add(Team(**t_data))
    db.commit()

    it_team = db.query(Team).filter(Team.name == "IT & Security").first()

    # 3. Seed Users (Updated: admin, mimi, mai)
    users_data = [
        {
            "username": "admin",
            "email": "admin@isms.local",
            "full_name": "System Administrator",
            "password": "Admin@123456",
            "role_id": 4,
            "team_id": it_team.id if it_team else None
        },
        {
            "username": "mimi",
            "email": "mimi@isms.local",
            "full_name": "Mimi (Standard User)",
            "password": "User@123456",
            "role_id": 5,
            "team_id": it_team.id if it_team else None
        },
        {
            "username": "mai",
            "email": "mai@isms.local",
            "full_name": "Mai (ISMS Auditor)",
            "password": "Auditor@123456",
            "role_id": 6,
            "team_id": None
        }
    ]

    for u_data in users_data:
        user = db.query(User).filter(User.username == u_data["username"]).first()
        if not user:
            new_user = User(
                username=u_data["username"],
                email=u_data["email"],
                full_name=u_data["full_name"],
                hashed_password=get_password_hash(u_data["password"]),
                role_id=u_data["role_id"],
                team_id=u_data["team_id"],
                is_active=True
            )
            db.add(new_user)
    db.commit()
    print("✅ Database seeding with updated users (mimi, mai) completed!")

if __name__ == "__main__":
    db = SessionLocal()
    init_db(db)
    db.close()
