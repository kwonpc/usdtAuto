from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.database import Database
from app.service.bot_service import BotManager


def create_app() -> FastAPI:
    settings = get_settings()
    database = Database(settings)
    database.init()

    app = FastAPI(title="KRW-USDT Premium Trading Bot", version="0.1.0")
    bot_manager = BotManager(settings, database)
    scheduler = AsyncIOScheduler()

    app.state.settings = settings
    app.state.database = database
    app.state.bot_manager = bot_manager
    app.state.scheduler = scheduler

    @app.on_event("startup")
    async def startup() -> None:
        scheduler.add_job(bot_manager.tick_all, "interval", seconds=settings.poll_interval_seconds, id="bot_tick")
        scheduler.start()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        scheduler.shutdown(wait=False)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse("app/static/index.html")

    app.include_router(router)
    return app


app = create_app()
