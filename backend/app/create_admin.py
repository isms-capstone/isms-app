"""Create an initial Admin account if one does not already exist.

For production, provide credentials through a secure deployment process and change
the development password immediately. This script never resets an existing account.
"""
from app.db.session import SessionLocal, engine, Base
from app.db.models.user import User, Role
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)

DEFAULT_USERNAME = "admin"
DEFAULT_EMAIL = "admin@isms.local"
DEVELOPMENT_PASSWORD = "Admin@123456"


def create_admin():
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "Admin").first()
        if role is None:
            role = Role(name="Admin", description="System administrator")
            db.add(role)
            db.flush()

        user = db.query(User).filter(User.username == DEFAULT_USERNAME).first()
        if user is None:
            user = User(
                username=DEFAULT_USERNAME,
                email=DEFAULT_EMAIL,
                full_name="System Administrator",
                hashed_password=get_password_hash(DEVELOPMENT_PASSWORD),
                is_active=True,
                role_id=role.id,
            )
            db.add(user)
            db.commit()
            print("Created initial Admin account. Change its development password before production.")
        else:
            print("Admin username already exists; existing credentials were left unchanged.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
