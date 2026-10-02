from typing import Optional, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.db.models.user import User
from app.core import security
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Role names are the business identifiers defined by SRS, not database IDs.
SYSTEM_ROLE_NAMES = {
    "Admin",
    "Agent",
    "Specialist",
    "Developer",
    "Team Lead",
    "Executive",
}


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("type")
        if not username or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.username == username)
        .first()
    )
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


class RoleChecker:
    """Authorize by role name, independent of the role's database primary key."""

    def __init__(self, allowed_roles: Optional[Sequence[str]] = None):
        # None means any authenticated user; a sequence means explicit role allow-list.
        self.allowed_roles = set(allowed_roles) if allowed_roles is not None else None

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        role_name = current_user.role.name if current_user.role else None
        if self.allowed_roles is not None and role_name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: insufficient privileges.",
            )
        return current_user


require_admin = RoleChecker(["Admin"])
# Executive can view assets; creation remains Admin-only.
require_admin_or_auditor = RoleChecker(["Admin", "Executive"])
require_any_authenticated = RoleChecker()
