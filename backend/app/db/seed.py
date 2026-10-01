from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.user import User, Role, Team
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_data():
    db: Session = SessionLocal()
    try:
        # 1. Create Default Roles
        roles_data = [
            {"name": "Admin", "description": "System Administrator with full access"},
            {"name": "User", "description": "Standard User"},
            {"name": "Auditor", "description": "Read-only access for compliance auditing"},
        ]
        
        roles = {}
        for r_data in roles_data:
            role = db.query(Role).filter(Role.name == r_data["name"]).first()
            if not role:
                role = Role(**r_data)
                db.add(role)
                db.flush()
            roles[r_data["name"]] = role

        # 2. Create Default Team
        team = db.query(Team).filter(Team.name == "IT & Security").first()
        if not team:
            team = Team(name="IT & Security", description="Core IT Security Team")
            db.add(team)
            db.flush()

        # 3. Create Super Admin User
        admin_username = "admin"
        admin_user = db.query(User).filter(User.username == admin_username).first()
        if not admin_user:
            admin_user = User(
                username=admin_username,
                email="admin@isms.local",
                hashed_password=pwd_context.hash("Admin@123456"),
                full_name="System Administrator",
                is_active=True,
                role_id=roles["Admin"].id,
                team_id=team.id
            )
            db.add(admin_user)

        db.commit()
        print("✅ Seed data inserted successfully!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
