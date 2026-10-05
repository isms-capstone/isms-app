from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import Role, User
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.api.deps import require_admin, require_any_authenticated, SYSTEM_ROLE_NAMES

router = APIRouter()


def _get_role_or_404(db: Session, role_id: int) -> Role:
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    return role


@router.get("/", response_model=List[RoleOut], dependencies=[Depends(require_any_authenticated)])
def read_roles(db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.id).all()


@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_role(role_in: RoleCreate, db: Session = Depends(get_db)):
    if db.query(Role).filter(Role.name == role_in.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role already exists")
    role = Role(name=role_in.name, description=role_in.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.patch("/{role_id}", response_model=RoleOut, dependencies=[Depends(require_admin)])
def update_role(role_id: int, role_in: RoleUpdate, db: Session = Depends(get_db)):
    role = _get_role_or_404(db, role_id)
    data = role_in.model_dump(exclude_unset=True)
    if "name" in data:
        if role.name in SYSTEM_ROLE_NAMES and data["name"] != role.name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "System role cannot be renamed")
        if not data["name"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name cannot be empty")
        if db.query(Role).filter(Role.name == data["name"], Role.id != role.id).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role already exists")
    for field, value in data.items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_role(role_id: int, db: Session = Depends(get_db)):
    role = _get_role_or_404(db, role_id)
    if role.name in SYSTEM_ROLE_NAMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "System role cannot be deleted")
    if db.query(User).filter(User.role_id == role.id).count():
        raise HTTPException(status.HTTP_409_CONFLICT, "Role is still assigned to users")
    try:
        db.delete(role)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Role is referenced by other records")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
