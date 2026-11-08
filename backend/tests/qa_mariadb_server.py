"""Disposable CAT QA service. Refuses the normal application database port."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from sqlalchemy import select
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.db.models.user import Role, User

if settings.MARIADB_PORT != 5437 or settings.MARIADB_PASSWORD != 'cat-local-qa-only':
    raise RuntimeError('CAT browser QA must use the disposable localhost:5437 database')

with SessionLocal() as db:
    init_db(db)
    for name in ('Admin', 'Agent', 'Auditor'):
        if not db.scalar(select(Role).where(Role.name == name)):
            db.add(Role(name=name))
    db.flush()
    for username, name in [('qa-admin', 'Admin'), ('qa-agent', 'Agent'), ('qa-auditor', 'Auditor')]:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            role = db.scalar(select(Role).where(Role.name == name))
            db.add(User(username=username, email=f'{username}@cat-qa.invalid', role_id=role.id,
                        hashed_password=get_password_hash('test-only-password'), is_active=True))
    db.commit()

app = FastAPI(title='CAT disposable MariaDB QA')
app.include_router(api_router, prefix='/api/v1')
