from app.db.session import SessionLocal, engine, Base
from app.db.models.user import User, Role
from app.core.security import get_password_hash

# สร้าง Table ใน DB หากยังไม่มี
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 1. ตรวจสอบ/สร้าง Role 'admin' และ 'user'
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="System Administrator")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
        print("✅ สร้าง Role 'admin' เรียบร้อย")

    user_role = db.query(Role).filter(Role.name == "user").first()
    if not user_role:
        user_role = Role(name="user", description="Standard User")
        db.add(user_role)
        db.commit()
        print("✅ สร้าง Role 'user' เรียบร้อย")

    # 2. ตรวจสอบ/สร้าง User 'admin'
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="System Admin",
            hashed_password=get_password_hash("Admin@123456"),
            is_active=True,
            role_id=admin_role.id
        )
        db.add(admin_user)
        db.commit()
        print("✅ สร้างบัญชี admin สำเร็จ! (Password: Admin@123456)")
    else:
        admin_user.hashed_password = get_password_hash("Admin@123456")
        admin_user.email = "admin@example.com"
        admin_user.is_active = True
        admin_user.role_id = admin_role.id
        db.commit()
        print("🔄 อัปเดตรหัสผ่านและสิทธิ์ของ admin เรียบร้อย!")

finally:
    db.close()