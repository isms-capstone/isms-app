from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.teams import router as teams_router
from app.api.v1.endpoints.assets import router as assets_router

from app.api.v1.endpoints.customers import router as customers_router
from app.api.v1.endpoints.products import router as products_router

api_router = APIRouter()
api_router.include_router(customers_router, prefix="/customers", tags=["Customer Registry"])
api_router.include_router(products_router, tags=["Product Registry"])

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users Management"])
api_router.include_router(teams_router, prefix="/teams", tags=["Teams Management"])
api_router.include_router(assets_router, prefix="/assets", tags=["Asset Management"])
