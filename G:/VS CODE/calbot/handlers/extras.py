from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.food_log import FoodLog
from models.weight_log import WeightLog
from models.water_log import WaterLog
from models.saved_meal import SavedMeal
from services.stats import get_daily_totals
from config import MEAL_TYPES

router = Router()

WATER_GOAL = 8
MEAL_EMOJI = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"}


class WeightState(StatesGroup):
    entering = State()


# ─────────────────────────── WATER ───────────────────────────

@router.message(Command("water"))
async def cmd_water(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    today = date.today()
    log = await session.scalar(
        select(WaterLog).where(WaterLog.telegram_id == message.from_user.id, WaterLog.log_date == today)
    )
    if not log:
        log = WaterLog(telegram_id=message.from_user.id, log_date=today, glasses=0)
        session.add(log)

    log.glasses += 1
    await session.commit()

    filled = "💧" * log.glasses + "⬜" * max(0, WATER_GOAL - log.glasses)
    pct = round(log.glasses / WATER_GOAL * 100)

    if log.glasses >= WATER_GOAL:
        status = "🎉 Дневная норма выполнена! Отлично!"
    else:
        left = WATER_GOAL - log.glasses
        status = f"Осталось ещё {left} стакана{'!' if left == 1 else 'ов!'}"

    await message.answer(
        f"💧 <b>Водный баланс</b>\n\n"
        f"{filled}\n"
        f"{log.glasses} / {WATER_GOAL} стаканов ({pct}%)\n\n"
        f"{status}",
        parse_mode="HTML"
    )


# ─────────────────────────── WEIGHT ───────────────────────────

@router.message(Command("weight"))
async def cmd_weight(message: Message, state: FSMContext, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    logs = (await session.execute(
        select(WeightLog)
        .where(WeightLog.telegram_id == message.from_user.id)
        .order_by(desc(WeightLog.log_date))
        .limit(5)
    )).scalars().all()

    history = ""
    if logs:
        history = "\n📈 <b>История:</b>\n"
        for log in reversed(logs):
            history += f"  {log.log_date.strftime('%d.%m')} — {log.weight_kg} кг\n"
        first = logs[-1].weight_kg
        last = logs[0].weight_kg
        diff = round(last - first, 1)
        sign = "+" if diff > 0 else ""
        history += f"\nДинамика: <b>{sign}{diff} кг</b>"

    await state.set_state(WeightState.entering)
    await message.answer(
        f"⚖️ <b>Запись веса</b>{history}\n\n"
        f"Введи текущий вес в кг:",
        parse_mode="HTML"
    )


@router.message(WeightState.entering)
async def process_weight(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text:
        await message.answer("Введи вес цифрами, например: <code>74.5</code>", parse_mode="HTML")
        return
    try:
        weight = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи вес цифрами, например: <code>74.5</code>", parse_mode="HTML")
        return
    if not (20 <= weight <= 300):
        await message.answer("Введи реальный вес от 20 до 300 кг.")
        return

    user = await session.get(User, message.from_user.id)
    today = date.today()

    existing = await session.scalar(
        select(WeightLog).where(WeightLog.telegram_id == message.from_user.id, WeightLog.log_date == today)
    )
    if existing:
        existing.weight_kg = weight
    else:
        session.add(WeightLog(telegram_id=message.from_user.id, log_date=today, weight_kg=weight))

    old_weight = user.weight_kg or weight
    user.weight_kg = weight
    await session.commit()
    await state.clear()

    diff = round(weight - old_weight, 1)
    sign = "+" if diff > 0 else ""
    diff_text = f" ({sign}{diff} кг от профиля)" if diff != 0 else ""

    await message.answer(
        f"✅ Вес записан: <b>{weight} кг</b>{diff_text}\n\n"
        f"Профиль обновлён. Продолжай в том же духе! 💪",
        parse_mode="HTML"
    )


# ─────────────────────────── STREAK ───────────────────────────

@router.message(Command("streak"))
async def cmd_streak(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    streak = 0
    today = date.today()

    for i in range(1, 31):
        d = today - timedelta(days=i)
        totals = await get_daily_totals(session, message.from_user.id, d)
        if totals["calories"] > 0 and totals["calories"] <= user.daily_calories:
            streak += 1
        elif totals["calories"] == 0 and i == 1:
            continue
        else:
            break

    if streak == 0:
        text = (
            "🔥 <b>Твой стрик: 0 дней</b>\n\n"
            "Начни сегодня — внеси приём пищи в рамках нормы, "
            "и стрик запустится!\n\n"
            "Добавить еду: /add"
        )
    elif streak < 3:
        text = f"🔥 <b>Стрик: {streak} {'день' if streak == 1 else 'дня'}!</b>\n\nХорошее начало! Продолжай 💪"
    elif streak < 7:
        text = f"🔥🔥 <b>Стрик: {streak} дней!</b>\n\nОтличная работа! Ты в ударе! 💪"
    elif streak < 14:
        text = f"🔥🔥🔥 <b>Стрик: {streak} дней!</b>\n\nНеверoyatно! Ты настоящая машина! 🏆"
    else:
        text = f"⚡🔥 <b>СТРИК: {streak} ДНЕЙ!</b>\n\nТы легенда! Это невероятный результат! 🏆🏆"

    await message.answer(text, parse_mode="HTML")


# ─────────────────────────── SAVED MEALS ───────────────────────────

def saved_meal_keyboard(meals: list[SavedMeal]) -> InlineKeyboardMarkup:
    buttons = []
    for m in meals:
        label = f"⭐ {m.name[:28]} — {int(m.calories)} ккал"
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"saved_add:{m.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"saved_del:{m.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="saved_del:close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def meal_for_saved_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 Завтрак", callback_data="savedmeal:breakfast"),
            InlineKeyboardButton(text="☀️ Обед", callback_data="savedmeal:lunch"),
        ],
        [
            InlineKeyboardButton(text="🌙 Ужин", callback_data="savedmeal:dinner"),
            InlineKeyboardButton(text="🍎 Перекус", callback_data="savedmeal:snack"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="savedmeal:cancel")],
    ])


@router.message(Command("saved"))
async def cmd_saved(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    meals = (await session.execute(
        select(SavedMeal).where(SavedMeal.telegram_id == message.from_user.id)
    )).scalars().all()

    if not meals:
        await message.answer(
            "⭐ <b>Сохранённые блюда</b>\n\n"
            "У тебя пока нет сохранённых блюд.\n\n"
            "После добавления еды через /add нажми «⭐ Сохранить» "
            "чтобы добавить в избранное.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"⭐ <b>Сохранённые блюда</b> ({len(meals)})\n\n"
        "Нажми на блюдо чтобы быстро добавить его сегодня:",
        reply_markup=saved_meal_keyboard(list(meals)),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("saved_del:"))
async def delete_saved(callback: CallbackQuery, session: AsyncSession):
    action = callback.data.split(":")[1]
    if action == "close":
        await callback.message.delete()
        return
    meal = await session.get(SavedMeal, int(action))
    if meal and meal.telegram_id == callback.from_user.id:
        name = meal.name
        await session.delete(meal)
        await session.commit()
        await callback.answer(f"Удалено: {name}")

    meals = (await session.execute(
        select(SavedMeal).where(SavedMeal.telegram_id == callback.from_user.id)
    )).scalars().all()

    if not meals:
        await callback.message.edit_text("⭐ Список сохранённых блюд пуст.")
    else:
        await callback.message.edit_reply_markup(reply_markup=saved_meal_keyboard(list(meals)))


@router.callback_query(F.data.startswith("saved_add:"))
async def quick_add_saved(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    meal_id = int(callback.data.split(":")[1])
    meal = await session.get(SavedMeal, meal_id)
    if not meal or meal.telegram_id != callback.from_user.id:
        await callback.answer("Блюдо не найдено.", show_alert=True)
        return
    await state.update_data(pending_saved_id=meal_id)
    await callback.message.edit_text(
        f"⭐ <b>{meal.name}</b>\n"
        f"{int(meal.amount_g)} г — {int(meal.calories)} ккал\n\n"
        "Выбери приём пищи:",
        reply_markup=meal_for_saved_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("savedmeal:"))
async def save_to_log(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    meal_type = callback.data.split(":")[1]
    if meal_type == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    data = await state.get_data()
    meal_id = data.get("pending_saved_id")
    meal = await session.get(SavedMeal, meal_id)
    if not meal:
        await callback.answer("Блюдо не найдено.", show_alert=True)
        return

    session.add(FoodLog(
        telegram_id=callback.from_user.id,
        log_date=date.today(),
        meal_type=meal_type,
        food_name=meal.name,
        amount_g=meal.amount_g,
        calories=meal.calories,
        protein=meal.protein,
        fat=meal.fat,
        carbs=meal.carbs,
    ))
    await session.commit()
    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Добавлено!</b>\n\n"
        f"{MEAL_TYPES[meal_type]}: {meal.name} — {int(meal.calories)} ккал\n\n"
        f"/today — дневник  /left — остаток",
        parse_mode="HTML"
    )


# ─────────────────────────── SAVE MEAL CALLBACK ───────────────────────────

@router.callback_query(F.data.startswith("save_meal:"))
async def handle_save_meal(callback: CallbackQuery, session: AsyncSession):
    entry_id = int(callback.data.split(":")[1])
    entry = await session.get(FoodLog, entry_id)
    if not entry or entry.telegram_id != callback.from_user.id:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    existing = await session.scalar(
        select(SavedMeal).where(
            SavedMeal.telegram_id == callback.from_user.id,
            SavedMeal.name == entry.food_name,
        )
    )
    if existing:
        await callback.answer("Уже в сохранённых ⭐", show_alert=True)
        return

    session.add(SavedMeal(
        telegram_id=callback.from_user.id,
        name=entry.food_name,
        amount_g=entry.amount_g,
        calories=entry.calories,
        protein=entry.protein,
        fat=entry.fat,
        carbs=entry.carbs,
    ))
    await session.commit()
    await callback.answer("⭐ Сохранено в избранное!")


# ─────────────────────────── RECENT ───────────────────────────

@router.message(Command("recent"))
async def cmd_recent(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    rows = (await session.execute(
        select(FoodLog)
        .where(FoodLog.telegram_id == message.from_user.id)
        .order_by(desc(FoodLog.added_at))
        .limit(20)
    )).scalars().all()

    seen, recent = set(), []
    for r in rows:
        if r.food_name not in seen:
            seen.add(r.food_name)
            recent.append(r)
        if len(recent) == 5:
            break

    if not recent:
        await message.answer("Пока нет истории. Добавь первый приём пищи: /add")
        return

    buttons = []
    for r in recent:
        label = f"🔄 {r.food_name[:30]} ({int(r.amount_g)}г) — {int(r.calories)} ккал"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"recent_add:{r.id}")])
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="recent_close")])

    await message.answer(
        "🔄 <b>Последние блюда</b>\n\nНажми чтобы быстро добавить снова:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "recent_close")
async def recent_close(callback: CallbackQuery):
    await callback.message.delete()


@router.callback_query(F.data.startswith("recent_add:"))
async def recent_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    entry_id = int(callback.data.split(":")[1])
    entry = await session.get(FoodLog, entry_id)
    if not entry or entry.telegram_id != callback.from_user.id:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    await state.update_data(recent_entry_id=entry_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 Завтрак", callback_data="recentmeal:breakfast"),
            InlineKeyboardButton(text="☀️ Обед", callback_data="recentmeal:lunch"),
        ],
        [
            InlineKeyboardButton(text="🌙 Ужин", callback_data="recentmeal:dinner"),
            InlineKeyboardButton(text="🍎 Перекус", callback_data="recentmeal:snack"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="recentmeal:cancel")],
    ])
    await callback.message.edit_text(
        f"🔄 <b>{entry.food_name}</b> ({int(entry.amount_g)} г)\n\nВыбери приём пищи:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("recentmeal:"))
async def recent_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    meal_type = callback.data.split(":")[1]
    if meal_type == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    data = await state.get_data()
    entry = await session.get(FoodLog, data.get("recent_entry_id"))
    if not entry:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    session.add(FoodLog(
        telegram_id=callback.from_user.id,
        log_date=date.today(),
        meal_type=meal_type,
        food_name=entry.food_name,
        amount_g=entry.amount_g,
        calories=entry.calories,
        protein=entry.protein,
        fat=entry.fat,
        carbs=entry.carbs,
    ))
    await session.commit()
    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Добавлено!</b>\n\n"
        f"{MEAL_TYPES[meal_type]}: {entry.food_name} — {int(entry.calories)} ккал\n\n"
        f"/today — дневник  /left — остаток",
        parse_mode="HTML"
    )
