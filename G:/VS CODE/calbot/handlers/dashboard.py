from datetime import date
import io

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from models.user import User
from models.food_log import FoodLog
from services.stats import get_today_entries, get_daily_totals, get_week_data, progress_bar
from utils.charts import make_week_chart
from config import MEAL_TYPES

router = Router()

MEAL_EMOJI = {
    "breakfast": "🌅",
    "lunch": "☀️",
    "dinner": "🌙",
    "snack": "🍎",
}

WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS_RU = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def format_date(d: date) -> str:
    return f"{WEEKDAYS_RU[d.weekday()].capitalize()}, {d.day} {MONTHS_RU[d.month]}"


def delete_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{entry_id}")
    ]])


@router.message(Command("today"))
async def cmd_today(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    today = date.today()
    entries = await get_today_entries(session, message.from_user.id, today)
    totals = await get_daily_totals(session, message.from_user.id, today)

    cal_bar = progress_bar(totals["calories"], user.daily_calories)
    p_bar = progress_bar(totals["protein"], user.daily_protein)
    f_bar = progress_bar(totals["fat"], user.daily_fat)
    c_bar = progress_bar(totals["carbs"], user.daily_carbs)

    text = (
        f"📊 <b>Дневник — {format_date(today)}</b>\n\n"
        f"🔥 Калории: {cal_bar}\n"
        f"    <b>{int(totals['calories'])}</b> / {user.daily_calories} ккал\n"
        f"🥩 Белки: <b>{int(totals['protein'])}</b> / {user.daily_protein} г\n"
        f"🧈 Жиры: <b>{int(totals['fat'])}</b> / {user.daily_fat} г\n"
        f"🍞 Углеводы: <b>{int(totals['carbs'])}</b> / {user.daily_carbs} г\n"
    )

    if not entries:
        text += "\n<i>Записей пока нет. Отправь фото еды или /add</i>"
        await message.answer(text, parse_mode="HTML")
        return

    # Group by meal type
    by_meal: dict[str, list[FoodLog]] = {}
    for e in entries:
        by_meal.setdefault(e.meal_type, []).append(e)

    text += "\n"
    for meal_key in ["breakfast", "lunch", "dinner", "snack"]:
        meal_entries = by_meal.get(meal_key, [])
        if not meal_entries:
            continue
        emoji = MEAL_EMOJI[meal_key]
        label = MEAL_TYPES[meal_key]
        meal_cal = sum(e.calories for e in meal_entries)
        text += f"\n{emoji} <b>{label}</b> — {int(meal_cal)} ккал\n"
        for e in meal_entries:
            text += f"  • {e.food_name} ({int(e.amount_g)}г) — {int(e.calories)} ккал\n"

    left_cal = user.daily_calories - totals["calories"]
    if left_cal > 0:
        text += f"\n💡 Осталось: <b>{int(left_cal)} ккал</b>"
    else:
        text += f"\n⚠️ Превышение на <b>{int(abs(left_cal))} ккал</b>"

    text += "\n\n<i>Для удаления записи нажми /delete</i>"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("left"))
async def cmd_left(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    totals = await get_daily_totals(session, message.from_user.id, date.today())

    left_cal = user.daily_calories - totals["calories"]
    left_p = user.daily_protein - totals["protein"]
    left_f = user.daily_fat - totals["fat"]
    left_c = user.daily_carbs - totals["carbs"]

    cal_bar = progress_bar(totals["calories"], user.daily_calories)

    if left_cal > 0:
        status = f"✅ Осталось <b>{int(left_cal)} ккал</b>"
    else:
        status = f"⚠️ Превышение на <b>{int(abs(left_cal))} ккал</b>"

    await message.answer(
        f"⚡ <b>Остаток на сегодня</b>\n\n"
        f"🔥 {cal_bar}\n"
        f"   {int(totals['calories'])} / {user.daily_calories} ккал\n\n"
        f"{status}\n\n"
        f"🥩 Белки: осталось <b>{int(max(left_p, 0))} г</b>\n"
        f"🧈 Жиры: осталось <b>{int(max(left_f, 0))} г</b>\n"
        f"🍞 Углеводы: осталось <b>{int(max(left_c, 0))} г</b>",
        parse_mode="HTML"
    )


@router.message(Command("week"))
async def cmd_week(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    wait_msg = await message.answer("📊 Готовлю недельный отчёт...")
    week = await get_week_data(session, message.from_user.id)

    active_days = [d for d in week if d["calories"] > 0]
    avg_cal = round(sum(d["calories"] for d in active_days) / len(active_days)) if active_days else 0

    best = max(active_days, key=lambda d: d["calories"]) if active_days else None
    worst = min(active_days, key=lambda d: d["calories"]) if len(active_days) > 1 else None

    days_in_norm = sum(1 for d in active_days if d["calories"] <= user.daily_calories)

    text = (
        f"📅 <b>Отчёт за 7 дней</b>\n\n"
        f"🔥 Среднее: <b>{avg_cal} ккал</b> (лимит {user.daily_calories})\n"
        f"✅ Дней в норме: <b>{days_in_norm} из {len(active_days)}</b>\n"
    )
    if best:
        text += f"🏆 Максимум: {best['date'].strftime('%d.%m')} — {int(best['calories'])} ккал\n"
    if worst:
        text += f"📉 Минимум: {worst['date'].strftime('%d.%m')} — {int(worst['calories'])} ккал\n"

    chart_bytes = make_week_chart(week, user.daily_calories)
    chart_file = BufferedInputFile(chart_bytes, filename="week_chart.png")

    await wait_msg.delete()
    await message.answer_photo(chart_file, caption=text, parse_mode="HTML")


@router.message(Command("delete"))
async def cmd_delete(message: Message, session: AsyncSession):
    entries = await get_today_entries(session, message.from_user.id, date.today())
    if not entries:
        await message.answer("Сегодня нет записей для удаления.")
        return

    text = "🗑 <b>Выбери запись для удаления:</b>\n\n"
    buttons = []
    for e in entries:
        meal_emoji = MEAL_EMOJI.get(e.meal_type, "🍽")
        label = f"{meal_emoji} {e.food_name[:30]} ({int(e.amount_g)}г) — {int(e.calories)} ккал"
        text += f"• {label}\n"
        buttons.append([InlineKeyboardButton(text=f"🗑 {e.food_name[:25]}", callback_data=f"del:{e.id}")])

    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="del:close")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("del:"))
async def process_delete(callback: CallbackQuery, session: AsyncSession):
    action = callback.data.split(":")[1]

    if action == "close":
        await callback.message.delete()
        return

    entry_id = int(action)
    entry = await session.get(FoodLog, entry_id)

    if not entry or entry.telegram_id != callback.from_user.id:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    food_name = entry.food_name
    calories = entry.calories
    await session.delete(entry)
    await session.commit()

    await callback.answer(f"Удалено: {food_name}")
    await callback.message.edit_text(
        f"🗑 Удалено: <b>{food_name}</b> — {int(calories)} ккал\n\n"
        f"Обновить дневник: /today",
        parse_mode="HTML"
    )
