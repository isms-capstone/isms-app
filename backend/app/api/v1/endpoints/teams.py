from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import Team
from app.schemas.team import TeamCreate, TeamResponse
from app.api.deps import require_admin, require_any_authenticated

router = APIRouter()

@router.get("/", response_model=List[TeamResponse], dependencies=[Depends(require_any_authenticated)])
def read_teams(db: Session = Depends(get_db)):
    return db.query(Team).all()

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_team(team_in: TeamCreate, db: Session = Depends(get_db)):
    db_team = db.query(Team).filter(Team.name == team_in.name).first()
    if db_team:
        raise HTTPException(status_code=400, detail="Team already exists")
    team = Team(name=team_in.name, description=team_in.description)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
