from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetResponse
from app.api.deps import require_admin, require_admin_or_auditor

router = APIRouter()

@router.get("/", response_model=List[AssetResponse], dependencies=[Depends(require_admin_or_auditor)])
def read_assets(db: Session = Depends(get_db)):
    return db.query(Asset).all()

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_asset(asset_in: AssetCreate, db: Session = Depends(get_db)):
    db_asset = db.query(Asset).filter(Asset.asset_code == asset_in.asset_code).first()
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset code already exists")
    asset = Asset(**asset_in.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
