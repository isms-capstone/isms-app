from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.core import security
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[int]):
        """
        allowed_roles: รายชื่อ Role ID ที่อนุญาต
        (เช่น Admin = 4, User = 5, Auditor = 6)
        """
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_id not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: You do not have sufficient privileges to access this resource."
            )
        return current_user

# --- Pre-defined Permission Dependencies ---
require_admin = RoleChecker(allowed_roles=[4])                  # เฉพาะ Admin เท่านั้น
require_admin_or_auditor = RoleChecker(allowed_roles=[4, 6])   # Admin หรือ Auditor
require_any_authenticated = RoleChecker(allowed_roles=[4, 5, 6]) # ผู้ใช้งานระบบทุกคน