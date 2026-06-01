import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database import init_db, AsyncSessionLocal
from handlers import start, onboarding, profile, food_add, food_photo, dashboard, notifications, extras
from services.scheduler import setup_scheduler
from api.routes import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FatBot API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Health check (must be before StaticFiles mount)
@app.get("/health")
async def health():
    return "OK"

# Serve mini app static files — mount LAST so /api/* routes take priority
_miniapp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "miniapp")
if os.path.exists(_miniapp_dir):
    app.mount("/", StaticFiles(directory=_miniapp_dir, html=True), name="miniapp")


async def db_session_middleware(handler, event, data):
    async with AsyncSessionLocal() as session:
        data["session"] = session
        return await handler(event, data)


async def run_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(db_session_middleware)
    dp.include_router(start.router)
    dp.include_router(onboarding.router)
    dp.include_router(profile.router)
    dp.include_router(food_add.router)
    dp.include_router(food_photo.router)
    dp.include_router(dashboard.router)
    dp.include_router(notifications.router)
    dp.include_router(extras.router)

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    setup_scheduler(scheduler, bot)
    scheduler.start()
    logger.info("Bot + scheduler started")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()


async def main():
    await init_db()
    logger.info("Database initialized")

    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        run_bot(),
    )


if __name__ == "__main__":
    asyncio.run(main())
