from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import Team, User
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.api.deps import require_admin, require_any_authenticated

router = APIRouter()


def _get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return team


@router.get("/", response_model=List[TeamResponse], dependencies=[Depends(require_any_authenticated)])
def read_teams(db: Session = Depends(get_db)):
    return db.query(Team).order_by(Team.id).all()


@router.get("/{team_id}", response_model=TeamResponse, dependencies=[Depends(require_any_authenticated)])
def read_team(team_id: int, db: Session = Depends(get_db)):
    return _get_team_or_404(db, team_id)


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_team(team_in: TeamCreate, db: Session = Depends(get_db)):
    if db.query(Team).filter(Team.name == team_in.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Team already exists")
    team = Team(name=team_in.name, description=team_in.description)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.patch("/{team_id}", response_model=TeamResponse, dependencies=[Depends(require_admin)])
def update_team(team_id: int, team_in: TeamUpdate, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    data = team_in.model_dump(exclude_unset=True)
    if "name" in data:
        if not data["name"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name cannot be empty")
        if db.query(Team).filter(Team.name == data["name"], Team.id != team.id).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Team already exists")
    for field, value in data.items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_team(team_id: int, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    if db.query(User).filter(User.team_id == team.id).count():
        raise HTTPException(status.HTTP_409_CONFLICT, "Team still has members. Move them to another team first.")
    try:
        db.delete(team)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Team is referenced by other records")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
