from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.user import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        session.add(user)
        await session.commit()

    if not user.is_onboarded:
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я CalBot — твой личный нутрициолог в Telegram.\n\n"
            "Я помогу тебе:\n"
            "🍽 Считать калории по фото и тексту\n"
            "📊 Отслеживать КБЖУ каждый день\n"
            "🏆 Достигать твоих целей по весу\n"
            "🔔 Напоминать о приёмах пищи\n\n"
            "Сначала давай настроим твой профиль.\n"
            "Введи /setup чтобы начать ⚙️"
        )
    else:
        await message.answer(
            f"С возвращением, {message.from_user.first_name}! 💪\n\n"
            "Что делаем?\n"
            "/today — дневник за сегодня\n"
            "/add — добавить еду\n"
            "/left — остаток калорий\n"
            "/help — все команды"
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 <b>Все команды CalBot</b>\n\n"
        "<b>Основное:</b>\n"
        "/today — дневник питания за сегодня\n"
        "/add — добавить еду (текст или фото)\n"
        "/left — сколько калорий осталось\n\n"
        "<b>Прогресс:</b>\n"
        "/week — отчёт за неделю\n"
        "/weight — записать вес\n"
        "/streak — твой стрик\n\n"
        "<b>Вода:</b>\n"
        "/water — добавить стакан воды\n\n"
        "<b>Настройки:</b>\n"
        "/profile — мой профиль и лимиты\n"
        "/settings — настройки уведомлений\n"
        "/setup — пересчитать профиль\n\n"
        "<b>Другое:</b>\n"
        "/saved — избранные блюда\n"
        "/help — эта справка",
        parse_mode="HTML"
    )
