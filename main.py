import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from config import BOT_TOKEN
from database import init_db, AsyncSessionLocal
from handlers import start, onboarding, profile, food_add, food_photo, dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


async def db_session_middleware(handler, event, data):
    async with AsyncSessionLocal() as session:
        data["session"] = session
        return await handler(event, data)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(db_session_middleware)

    dp.include_router(start.router)
    dp.include_router(onboarding.router)
    dp.include_router(profile.router)
    dp.include_router(food_add.router)
    dp.include_router(food_photo.router)
    dp.include_router(dashboard.router)

    await init_db()
    logger.info("Database initialized")

    logger.info("Bot started")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
