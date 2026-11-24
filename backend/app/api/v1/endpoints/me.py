from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import get_password_hash, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import UserResponse, UserSelfUpdate


router = APIRouter(
    tags=["User Profile"],
)


@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    user_in: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = user_in.model_dump(exclude_unset=True)

    if not data:
        return current_user

    if "email" in data and data["email"] != current_user.email:
        existing_user = (
            db.query(User)
            .filter(
                User.email == data["email"],
                User.id != current_user.id,
            )
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="อีเมลนี้ถูกใช้แล้ว",
            )

    for field, value in data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/me/change-password")
def change_my_password(
    current_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(
        current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รหัสผ่านปัจจุบันไม่ถูกต้อง",
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รหัสผ่านใหม่ต้องไม่ซ้ำรหัสผ่านเดิม",
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร",
        )

    current_user.hashed_password = get_password_hash(new_password)

    db.commit()

    return {
        "message": "Password changed successfully"
    }