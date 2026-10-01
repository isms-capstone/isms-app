from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.api.deps import get_current_user, require_admin, require_any_authenticated

router = APIRouter()

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(require_any_authenticated)])
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user_in.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    # โค้ดสร้าง User เพิ่มเติมตามที่มี
    return db_user
