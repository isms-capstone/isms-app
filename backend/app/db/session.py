from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base_class import Base

db_url = getattr(
    settings, 
    "SQLALCHEMY_DATABASE_URI", 
    getattr(settings, "DATABASE_URL", getattr(settings, "SQLALCHEMY_DATABASE_URL", None))
)

if not db_url:
    db_url = f"mysql+pymysql://{getattr(settings, 'MARIADB_USER', 'root')}:{getattr(settings, 'MARIADB_PASSWORD', '')}@{getattr(settings, 'MARIADB_SERVER', 'localhost')}:{getattr(settings, 'MARIADB_PORT', 3306)}/{getattr(settings, 'MARIADB_DB', 'isms_db')}"

engine = create_engine(
    db_url,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()