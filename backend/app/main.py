from fastapi import FastAPI
from app.core.config import settings
from app.modules.health.router import router as health_router

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(health_router)
