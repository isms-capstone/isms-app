from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.admin_users import router as admin_users_router
from app.api.v1.endpoints.teams import router as teams_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.assets import router as assets_router
from app.api.v1.endpoints.me import router as me_router
from app.api.v1.endpoints.master_data import router as master_data_router


api_router = APIRouter()


api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    admin_users_router,
)

api_router.include_router(
    teams_router,
    prefix="/teams",
    tags=["Teams Management"],
)

api_router.include_router(
    roles_router,
    prefix="/roles",
    tags=["Roles Management"],
)

api_router.include_router(
    assets_router,
    prefix="/assets",
    tags=["Asset Management"],
)

api_router.include_router(
    me_router
)
api_router.include_router(master_data_router)
