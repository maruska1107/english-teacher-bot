from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "english-teacher-bot"}


@router.get("/ready")
def ready() -> dict[str, str]:
    with SessionLocal() as session:
        _ping_database(session)
    return {"status": "ready", "database": "ok"}


def _ping_database(session: Session) -> None:
    session.execute(text("SELECT 1"))
