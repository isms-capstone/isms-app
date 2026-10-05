from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.db.models.user import User, Role, Team
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.security import get_password_hash
from app.api.deps import get_current_user, require_admin

from fastapi import APIRouter

router = APIRouter(
    prefix="/admin/users",
    tags=["Admin - Users"],
)


# ---------- helpers ----------
def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user

def _get_role_by_name(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).first()

    if role is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Role not found: {role_name}",
        )

    return role


def _validate_role_team(db: Session, role_id: Optional[int], team_id: Optional[int]) -> None:
    if role_id is not None and not db.get(Role, role_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role not found")
    if team_id is not None and not db.get(Team, team_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Team not found")


def _guard_admin_loss(db: Session, user: User, actor: User) -> None:
    """กัน Admin ล็อกตัวเอง / ไม่ให้เหลือ Admin active เป็นศูนย์"""
    if user.id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You cannot suspend, delete or demote your own account",
        )
    is_admin = user.role is not None and user.role.name == "Admin"
    if is_admin and user.is_active:
        remaining = (
            db.query(User)
            .join(Role, User.role_id == Role.id)
            .filter(Role.name == "Admin", User.is_active.is_(True), User.id != user.id)
            .count()
        )
        if remaining < 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove the last active Admin")


# ---------- endpoints ----------

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(require_admin)])
def read_users(
    q: Optional[str] = Query(None, description="ค้นหา username / email / ชื่อ"),
    role_id: Optional[int] = None,
    team_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(User).options(joinedload(User.role), joinedload(User.team))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.username.like(like), User.email.like(like), User.full_name.like(like)))
    if role_id is not None:
        query = query.filter(User.role_id == role_id)
    if team_id is not None:
        query = query.filter(User.team_id == team_id)
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    return query.order_by(User.id).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
def read_user(user_id: int, db: Session = Depends(get_db)):
    return _get_user_or_404(db, user_id)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Username already registered",
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Email already registered",
        )

    role = _get_role_by_name(db, user_in.role)

    _validate_role_team(
        db,
        role.id,
        user_in.team_id,
    )

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role_id=role.id,
        team_id=user_in.team_id,
        is_active=user_in.is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)
    data = user_in.model_dump(exclude_unset=True)

    if "role" in data:
        role_name = data.pop("role")

        if role_name is None:
            raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "role cannot be null",
        )

        role = _get_role_by_name(db, role_name)
        data["role_id"] = role.id

    # role_id / is_active ห้ามเป็น null (team_id เป็น null ได้ = ถอดออกจากทีม)
    for required in ("role_id", "is_active", "email"):
        if required in data and data[required] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{required} cannot be null")

    if "email" in data and data["email"] != user.email:
        if db.query(User).filter(User.email == data["email"], User.id != user.id).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    _validate_role_team(db, data.get("role_id"), data.get("team_id"))

    current_is_admin = user.role is not None and user.role.name == "Admin"
    target_role = db.get(Role, data["role_id"]) if "role_id" in data else user.role
    demoting = "role_id" in data and target_role is not None and target_role.name != "Admin" and current_is_admin
    suspending = data.get("is_active") is False and user.is_active
    if suspending or demoting:
        _guard_admin_loss(db, user, actor)

    if "password" in data:
        pwd = data.pop("password")
        if pwd:
            user.hashed_password = get_password_hash(pwd)
    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/suspend", response_model=UserResponse)
def suspend_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    user = _get_user_or_404(db, user_id)
    if user.is_active:
        _guard_admin_loss(db, user, actor)
        user.is_active = False
        db.commit()
        db.refresh(user)
    return user


@router.post("/{user_id}/activate", response_model=UserResponse, dependencies=[Depends(require_admin)])
def activate_user(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    user = _get_user_or_404(db, user_id)
    _guard_admin_loss(db, user, actor)
    try:
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "User is referenced by other records (assets/cases). Suspend the user instead.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
