from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.calculator import format_profile_text

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)

    if not user or not user.is_onboarded:
        await message.answer(
            "Профиль ещё не настроен.\nВведи /setup чтобы начать ⚙️"
        )
        return

    await message.answer(format_profile_text(user), parse_mode="HTML")
