"""Ephemeral QA server; isolated temporary fixtures, actual login and RBAC."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.api.v1.router import api_router
from app.core.security import get_password_hash
from app.db.base_class import Base
from app.db.session import get_db
from app.db.models.user import Role, User, Team
from app.registry_ui import mount_registry_ui

temporary_db = TemporaryDirectory(prefix='isms-registry-qa-')
# Independent connections avoid sharing transaction state across parallel UI requests.
database_path = (Path(temporary_db.name) / 'registry.sqlite').as_posix()
engine = create_engine(f'sqlite:///{database_path}', connect_args={'check_same_thread': False})
@event.listens_for(engine, 'connect')
def foreign_keys(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')
Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine)
with factory() as db:
    db.add_all([Role(id=20, name='Admin'), Role(id=21, name='Agent'), Role(id=22, name='Auditor'), Team(name='Support')]); db.flush()
    hashed = get_password_hash('test-only-password')
    for username, role_id in [('qa-admin', 20), ('qa-agent', 21), ('qa-auditor', 22)]:
        db.add(User(username=username, email=f'{username}@example.org', role_id=role_id, hashed_password=hashed, is_active=True))
    db.commit()
app = FastAPI(); app.include_router(api_router, prefix='/api/v1'); mount_registry_ui(app)
def database():
    with factory() as db: yield db
app.dependency_overrides[get_db] = database

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8765)
