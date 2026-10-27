from fastapi import APIRouter

from app.api.routes import test, routes, route_profiles, route_visulization
from app.core.config import settings

api_router = APIRouter()

# include routes here
api_router.include_router(test.router)
api_router.include_router(routes.router)
api_router.include_router(route_profiles.router)
api_router.include_router(route_visulization.router)


