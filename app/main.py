from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.telegram.application import build_telegram_application, register_bot_commands


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    telegram_app = build_telegram_application()
    app.state.telegram_app = telegram_app
    if telegram_app is not None:
        await telegram_app.initialize()
        await register_bot_commands(telegram_app)
        if telegram_app.updater is not None:
            await telegram_app.updater.start_polling()
        await telegram_app.start()
    try:
        yield
    finally:
        if telegram_app is not None:
            if telegram_app.updater is not None:
                await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
