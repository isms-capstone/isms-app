from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import Team, User
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.users import require_admin

router = APIRouter()

@router.get("/", response_model=List[TeamResponse])
def read_teams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """ดึงรายชื่อ Team ทั้งหมด (ต้อง Authenticate แล้ว)"""
    teams = db.query(Team).offset(skip).limit(limit).all()
    return teams


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Any:
    """สร้าง Team ใหม่ (Admin Only)"""
    existing_team = db.query(Team).filter(Team.name == team_in.name).first()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name already exists"
        )
    
    db_team = Team(
        name=team_in.name,
        description=team_in.description
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    team_in: TeamUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Any:
    """แก้ไขข้อมูล Team (Admin Only)"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team_in.name is not None:
        db_team.name = team_in.name
    if team_in.description is not None:
        db_team.description = team_in.description
        
    db.commit()
    db.refresh(db_team)
    return db_team