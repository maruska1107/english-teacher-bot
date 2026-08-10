from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.landing import router as landing_router
from app.api.student_cards import homework_router as student_homework_router
from app.api.student_cards import router as student_cards_router
from app.api.student_webapp import router as student_webapp_router
from app.api.teacher_cards import profiles_router as teacher_card_profiles_router
from app.api.teacher_cards import router as teacher_cards_router
from app.api.teacher_webapp import router as teacher_webapp_router
from app.api.zoom import router as zoom_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(landing_router)
api_router.include_router(student_cards_router)
api_router.include_router(student_homework_router)
api_router.include_router(student_webapp_router)
api_router.include_router(teacher_card_profiles_router)
api_router.include_router(teacher_cards_router)
api_router.include_router(teacher_webapp_router)
api_router.include_router(zoom_router)
