from typing import List
from fastapi import Depends, HTTPException, status
from app.db.models.user import User
from app.api.v1.endpoints.auth import get_current_user

class RoleChecker:
    def __init__(self, allowed_roles: List[int]):
        """
        allowed_roles: รายชื่อ Role ID ที่อนุญาตให้ใช้งาน
        ตัวอย่าง: Admin = 4, User = 5, Auditor = 6
        """
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_id not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: You do not have sufficient privileges to access this resource."
            )
        return current_user

# Pre-defined Role Checkers
require_admin = RoleChecker(allowed_roles=[4])
require_admin_or_auditor = RoleChecker(allowed_roles=[4, 6])
require_any_authenticated = RoleChecker(allowed_roles=[4, 5, 6])