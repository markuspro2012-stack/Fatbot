from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.calculator import calculate_targets
from config import ACTIVITY_LABELS, GOAL_LABELS

router = Router()


class OnboardingStates(StatesGroup):
    gender = State()
    age = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👨 Мужской", callback_data="gender:male"),
        InlineKeyboardButton(text="👩 Женский", callback_data="gender:female"),
    ]])


def activity_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🪑 Сидячий (без спорта)", callback_data="activity:sedentary")],
        [InlineKeyboardButton(text="🚶 Лёгкий (1-2 тренировки)", callback_data="activity:light")],
        [InlineKeyboardButton(text="🏃 Умеренный (3-5 тренировок)", callback_data="activity:moderate")],
        [InlineKeyboardButton(text="💪 Активный (6-7 тренировок)", callback_data="activity:active")],
        [InlineKeyboardButton(text="🔥 Очень активный", callback_data="activity:very_active")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def goal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Похудеть", callback_data="goal:lose")],
        [InlineKeyboardButton(text="⚖️ Поддерживать вес", callback_data="goal:maintain")],
        [InlineKeyboardButton(text="📈 Набрать массу", callback_data="goal:gain")],
    ])


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(OnboardingStates.gender)
    await message.answer(
        "⚙️ <b>Настройка профиля</b>\n\n"
        "Шаг 1/6 — Укажи свой пол:",
        reply_markup=gender_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gender:"), OnboardingStates.gender)
async def process_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    await state.set_state(OnboardingStates.age)
    await callback.message.edit_text(
        "⚙️ <b>Настройка профиля</b>\n\n"
        "Шаг 2/6 — Сколько тебе лет?\n\n"
        "Введи число (например: <code>25</code>)",
        parse_mode="HTML"
    )


@router.message(OnboardingStates.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Введи возраст цифрами, например: <code>25</code>", parse_mode="HTML")
        return
    age = int(message.text)
    if not (10 <= age <= 100):
        await message.answer("Введи реальный возраст от 10 до 100 лет.")
        return
    await state.update_data(age=age)
    await state.set_state(OnboardingStates.height)
    await message.answer(
        "⚙️ <b>Настройка профиля</b>\n\n"
        "Шаг 3/6 — Твой рост в сантиметрах?\n\n"
        "Введи число (например: <code>175</code>)",
        parse_mode="HTML"
    )


@router.message(OnboardingStates.height)
async def process_height(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Введи рост цифрами, например: <code>175</code>", parse_mode="HTML")
        return
    height = int(message.text)
    if not (100 <= height <= 250):
        await message.answer("Введи реальный рост от 100 до 250 см.")
        return
    await state.update_data(height_cm=height)
    await state.set_state(OnboardingStates.weight)
    await message.answer(
        "⚙️ <b>Настройка профиля</b>\n\n"
        "Шаг 4/6 — Твой текущий вес в кг?\n\n"
        "Введи число (например: <code>75</code> или <code>75.5</code>)",
        parse_mode="HTML"
    )


@router.message(OnboardingStates.weight)
async def process_weight(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введи вес цифрами, например: <code>75</code>", parse_mode="HTML")
        return
    try:
        weight = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи вес цифрами, например: <code>75</code>", parse_mode="HTML")
        return
    if not (20 <= weight <= 300):
        await message.answer("Введи реальный вес от 20 до 300 кг.")
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(OnboardingStates.activity)
    await message.answer(
        "⚙️ <b>Настройка профиля</b>\n\n"
        "Шаг 5/6 — Уровень физической активности:",
        reply_markup=activity_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("activity:"), OnboardingStates.activity)
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split(":")[1]
    await state.update_data(activity_level=activity)
    await state.set_state(OnboardingStates.goal)
    await callback.message.edit_text(
        "⚙️ <b>Настройка профиля</b>\n\n"
        "Шаг 6/6 — Твоя цель:",
        reply_markup=goal_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("goal:"), OnboardingStates.goal)
async def process_goal(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    goal = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()

    targets = calculate_targets(
        gender=data["gender"],
        weight_kg=data["weight_kg"],
        height_cm=data["height_cm"],
        age=data["age"],
        activity_level=data["activity_level"],
        goal=goal,
    )

    user = await session.get(User, callback.from_user.id)
    user.gender = data["gender"]
    user.age = data["age"]
    user.height_cm = data["height_cm"]
    user.weight_kg = data["weight_kg"]
    user.activity_level = data["activity_level"]
    user.goal = goal
    user.daily_calories = targets["daily_calories"]
    user.daily_protein = targets["daily_protein"]
    user.daily_fat = targets["daily_fat"]
    user.daily_carbs = targets["daily_carbs"]
    user.is_onboarded = True
    await session.commit()

    goal_label = GOAL_LABELS[goal]
    await callback.message.edit_text(
        f"✅ <b>Профиль настроен!</b>\n\n"
        f"Цель: {goal_label}\n\n"
        f"📊 <b>Твои дневные лимиты:</b>\n\n"
        f"🔥 Калории: <b>{targets['daily_calories']} ккал</b>\n"
        f"🥩 Белки: <b>{targets['daily_protein']} г</b>\n"
        f"🧈 Жиры: <b>{targets['daily_fat']} г</b>\n"
        f"🍞 Углеводы: <b>{targets['daily_carbs']} г</b>\n\n"
        f"<i>Расчёт: BMR {targets['bmr']} ккал → TDEE {targets['tdee']} ккал</i>\n\n"
        f"Теперь начнём считать калории!\n"
        f"Отправь фото еды или /add чтобы добавить приём пищи 🍽",
        parse_mode="HTML"
    )
