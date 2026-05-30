import logging
from datetime import date

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from database import AsyncSessionLocal
from models.user import User
from services.stats import get_daily_totals, progress_bar

logger = logging.getLogger(__name__)


async def _get_notifiable_users(field: str) -> list[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.is_onboarded == True,
                getattr(User, field) == True,
            )
        )
        return list(result.scalars().all())


async def _safe_send(bot: Bot, telegram_id: int, text: str, **kwargs):
    try:
        await bot.send_message(telegram_id, text, **kwargs)
    except (TelegramForbiddenError, TelegramBadRequest):
        pass
    except Exception as e:
        logger.warning(f"Failed to send notification to {telegram_id}: {e}")


async def morning_briefing(bot: Bot):
    users = await _get_notifiable_users("notify_morning")
    for user in users:
        name = user.first_name or "друг"
        await _safe_send(
            bot, user.telegram_id,
            f"☀️ Доброе утро, {name}!\n\n"
            f"🎯 Цель на сегодня: <b>{user.daily_calories} ккал</b>\n"
            f"🥩 Белки: {user.daily_protein} г  "
            f"🧈 Жиры: {user.daily_fat} г  "
            f"🍞 Углеводы: {user.daily_carbs} г\n\n"
            f"Начни с хорошего завтрака! 🍳\n"
            f"Добавь приём пищи: /add",
            parse_mode="HTML"
        )


async def evening_summary(bot: Bot):
    users = await _get_notifiable_users("notify_evening")
    async with AsyncSessionLocal() as session:
        for user in users:
            totals = await get_daily_totals(session, user.telegram_id, date.today())
            bar = progress_bar(totals["calories"], user.daily_calories)
            left = user.daily_calories - totals["calories"]

            if totals["calories"] == 0:
                text = (
                    f"🌙 Добрый вечер!\n\n"
                    f"Похоже, сегодня ты ничего не записал.\n"
                    f"Не забывай вносить еду — это помогает достигать цели! 💪"
                )
            elif left > 0:
                text = (
                    f"🌙 <b>Итог дня</b>\n\n"
                    f"🔥 {bar}\n"
                    f"Съедено: <b>{int(totals['calories'])}</b> / {user.daily_calories} ккал\n\n"
                    f"✅ Отлично! Остаток {int(left)} ккал — держишь норму!\n"
                    f"Так держать! 🏆"
                )
            else:
                text = (
                    f"🌙 <b>Итог дня</b>\n\n"
                    f"🔥 {bar}\n"
                    f"Съедено: <b>{int(totals['calories'])}</b> / {user.daily_calories} ккал\n\n"
                    f"⚠️ Превышение на {int(abs(left))} ккал.\n"
                    f"Завтра начнём с чистого листа! 💪"
                )
            await _safe_send(bot, user.telegram_id, text, parse_mode="HTML")


async def meal_reminder(bot: Bot, meal: str):
    from config import MEAL_TYPES
    users = await _get_notifiable_users("notify_meals")
    meal_label = MEAL_TYPES.get(meal, meal)
    emoji = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}.get(meal, "🍽")

    for user in users:
        await _safe_send(
            bot, user.telegram_id,
            f"{emoji} Время {meal_label.lower()}!\n\n"
            f"Не забудь записать что съел. Отправь фото или /add",
        )


async def water_reminder(bot: Bot):
    users = await _get_notifiable_users("notify_water")
    for user in users:
        await _safe_send(
            bot, user.telegram_id,
            "💧 Выпей стакан воды!\n\nОтметить: /water"
        )


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot):
    scheduler.add_job(morning_briefing, "cron", hour=8, minute=0, args=[bot], id="morning")
    scheduler.add_job(evening_summary, "cron", hour=21, minute=0, args=[bot], id="evening")
    scheduler.add_job(meal_reminder, "cron", hour=9, minute=0, args=[bot, "breakfast"], id="remind_breakfast")
    scheduler.add_job(meal_reminder, "cron", hour=13, minute=0, args=[bot, "lunch"], id="remind_lunch")
    scheduler.add_job(meal_reminder, "cron", hour=19, minute=0, args=[bot, "dinner"], id="remind_dinner")
    for h in [10, 12, 14, 16, 18, 20]:
        scheduler.add_job(water_reminder, "cron", hour=h, minute=0, args=[bot], id=f"water_{h}")
    logger.info("Scheduler jobs registered")
