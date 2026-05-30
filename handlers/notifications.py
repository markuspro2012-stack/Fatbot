from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

router = Router()

NOTIFICATION_SETTINGS = [
    ("notify_morning", "☀️ Утренний брифинг (8:00)", "morning"),
    ("notify_meals",   "🍽 Напоминания о еде (9/13/19ч)", "meals"),
    ("notify_evening", "🌙 Вечерний итог (21:00)", "evening"),
    ("notify_water",   "💧 Напоминания о воде (каждые 2ч)", "water"),
]


def notifications_keyboard(user: User) -> InlineKeyboardMarkup:
    buttons = []
    for field, label, key in NOTIFICATION_SETTINGS:
        enabled = getattr(user, field)
        status = "✅" if enabled else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {label}",
            callback_data=f"notif_toggle:{field}"
        )])
    buttons.append([InlineKeyboardButton(text="✔️ Готово", callback_data="notif_toggle:close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_text(user: User) -> str:
    lines = ["🔔 <b>Настройки уведомлений</b>\n\nНажми чтобы включить / выключить:\n"]
    for field, label, _ in NOTIFICATION_SETTINGS:
        enabled = getattr(user, field)
        status = "включено" if enabled else "выключено"
        lines.append(f"{'✅' if enabled else '❌'} {label} — <i>{status}</i>")
    return "\n".join(lines)


@router.message(Command("notifications"))
async def cmd_notifications(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    await message.answer(
        settings_text(user),
        reply_markup=notifications_keyboard(user),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("notif_toggle:"))
async def toggle_notification(callback: CallbackQuery, session: AsyncSession):
    field = callback.data.split(":")[1]

    if field == "close":
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Настройки сохранены.")
        return

    user = await session.get(User, callback.from_user.id)
    if not user:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    current = getattr(user, field)
    setattr(user, field, not current)
    await session.commit()

    await callback.message.edit_text(
        settings_text(user),
        reply_markup=notifications_keyboard(user),
        parse_mode="HTML"
    )
    status = "включено ✅" if not current else "выключено ❌"
    await callback.answer(f"Уведомление {status}")
