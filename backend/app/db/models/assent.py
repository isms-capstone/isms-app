from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.db.session import Base

class AssetCategory(str, PyEnum):
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    DATA = "Data"
    PEOPLE = "People"
    SERVICE = "Service"

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, index=True, nullable=False) # รหัสทรัพย์สิน เช่น AST-001
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(AssetCategory), nullable=False, default=AssetCategory.HARDWARE)
    
    # CIA Assessment (1 = Low, 2 = Medium, 3 = High)
    confidentiality = Column(Integer, default=1)
    integrity = Column(Integer, default=1)
    availability = Column(Integer, default=1)

    # Relationships
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    owner = relationship("User", backref="assets")
    team = relationship("Team", backref="assets")