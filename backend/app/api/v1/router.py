from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.admin_users import router as admin_users_router
from app.api.v1.endpoints.teams import router as teams_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.assets import router as assets_router
from app.api.v1.endpoints.me import router as me_router
from app.api.v1.endpoints.master_data import router as master_data_router
from app.api.v1.endpoints.sla import router as sla_router


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
api_router.include_router(sla_router)

from app.api.v1.endpoints.customers import router as customers_router
from app.api.v1.endpoints.products import router as products_router
from app.api.v1.endpoints.customer_context import router as customer_context_router
from app.api.v1.endpoints.registry import router as registry_router
api_router.include_router(customers_router, prefix="/customers", tags=["Customer Registry"])
api_router.include_router(products_router, tags=["Product Registry"])
api_router.include_router(customer_context_router, prefix="/customers", tags=["Customer Context"])
api_router.include_router(registry_router, tags=["Registry Integration"])
from app.api.v1.endpoints.product_configuration import router as product_configuration_router
api_router.include_router(product_configuration_router, tags=["Product Configuration"])

from app.api.v1.endpoints.tickets import router as tickets_router
api_router.include_router(tickets_router, tags=["Case Capture"])

from app.api.v1.endpoints.customer_cases import router as customer_cases_router
api_router.include_router(customer_cases_router, tags=["Customer Cases"])
