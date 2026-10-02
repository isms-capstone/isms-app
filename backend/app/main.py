from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.v1.router import api_router
from app.db.session import SessionLocal
from app.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="ISMS Backend API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api/v1")

# Lightweight Admin UI (the API remains the source of authorization).
admin_static = Path(__file__).parent / "static" / "admin"
if admin_static.exists():
    app.mount("/admin", StaticFiles(directory=str(admin_static), html=True), name="admin")
