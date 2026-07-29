from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.landing import router as landing_router
from app.api.teacher_cards import router as teacher_cards_router
from app.api.teacher_webapp import router as teacher_webapp_router
from app.api.zoom import router as zoom_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(landing_router)
api_router.include_router(teacher_cards_router)
api_router.include_router(teacher_webapp_router)
api_router.include_router(zoom_router)
