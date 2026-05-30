from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.food_log import FoodLog
from services.food_api import search_food, calculate_portion
from config import MEAL_TYPES

router = Router()


class FoodAddStates(StatesGroup):
    meal_type = State()
    search_query = State()
    choosing_product = State()
    entering_grams = State()


def meal_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 Завтрак", callback_data="meal:breakfast"),
            InlineKeyboardButton(text="☀️ Обед", callback_data="meal:lunch"),
        ],
        [
            InlineKeyboardButton(text="🌙 Ужин", callback_data="meal:dinner"),
            InlineKeyboardButton(text="🍎 Перекус", callback_data="meal:snack"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="meal:cancel")],
    ])


def results_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for i, p in enumerate(products):
        label = f"{p['name'][:35]} · {p['kcal_100g']} ккал/100г"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"product:{i}")])
    buttons.append([InlineKeyboardButton(text="🔍 Искать заново", callback_data="product:retry")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="product:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Добавить", callback_data="confirm:yes"),
            InlineKeyboardButton(text="✏️ Изменить граммы", callback_data="confirm:edit"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:cancel")],
    ])


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    await state.clear()
    await state.set_state(FoodAddStates.meal_type)
    await message.answer(
        "🍽 <b>Добавить приём пищи</b>\n\nВыбери тип:",
        reply_markup=meal_type_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("meal:"), FoodAddStates.meal_type)
async def process_meal_type(callback: CallbackQuery, state: FSMContext):
    meal = callback.data.split(":")[1]

    if meal == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    await state.update_data(meal_type=meal)
    await state.set_state(FoodAddStates.search_query)
    meal_label = MEAL_TYPES[meal]

    await callback.message.edit_text(
        f"🍽 <b>{meal_label}</b>\n\n"
        "Что ты ел? Напиши название продукта или блюда:\n"
        "<i>Например: куриная грудка, гречка, творог</i>",
        parse_mode="HTML"
    )


@router.message(FoodAddStates.search_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip() if message.text else ""
    if not query:
        await message.answer("Введи название продукта или блюда:")
        return

    searching_msg = await message.answer("🔍 Ищу в базе продуктов...")
    products = await search_food(query)

    if not products:
        await searching_msg.edit_text(
            f"😕 По запросу «{query}» ничего не найдено.\n\n"
            "Попробуй другое название (на английском тоже работает):"
        )
        return

    await state.update_data(search_results=products, last_query=query)
    await state.set_state(FoodAddStates.choosing_product)

    await searching_msg.edit_text(
        f"🔍 Нашёл по запросу «{query}»:\n\n"
        "Выбери продукт из списка:",
        reply_markup=results_keyboard(products)
    )


@router.callback_query(F.data.startswith("product:"), FoodAddStates.choosing_product)
async def process_product_choice(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    if action == "retry":
        await state.set_state(FoodAddStates.search_query)
        await callback.message.edit_text(
            "Введи другое название продукта:"
        )
        return

    idx = int(action)
    data = await state.get_data()
    products = data["search_results"]
    product = products[idx]

    await state.update_data(selected_product=product)
    await state.set_state(FoodAddStates.entering_grams)

    await callback.message.edit_text(
        f"✅ <b>{product['name']}</b>\n\n"
        f"На 100 г: {product['kcal_100g']} ккал · "
        f"Б {product['protein_100g']}г · "
        f"Ж {product['fat_100g']}г · "
        f"У {product['carbs_100g']}г\n\n"
        "Сколько граммов ты съел?\n"
        "<i>Введи число, например: 150</i>",
        parse_mode="HTML"
    )


@router.message(FoodAddStates.entering_grams)
async def process_grams(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введи вес порции в граммах, например: <code>150</code>", parse_mode="HTML")
        return
    try:
        grams = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи вес цифрами, например: <code>150</code>", parse_mode="HTML")
        return
    if not (1 <= grams <= 5000):
        await message.answer("Введи реальный вес порции от 1 до 5000 г.")
        return

    data = await state.get_data()
    product = data["selected_product"]
    nutrition = calculate_portion(product, grams)

    await state.update_data(grams=grams, nutrition=nutrition)

    meal_label = MEAL_TYPES[data["meal_type"]]
    await message.answer(
        f"📋 <b>Подтверди добавление</b>\n\n"
        f"🍽 {meal_label}\n"
        f"🥘 {product['name']}\n"
        f"⚖️ {grams} г\n\n"
        f"🔥 {nutrition['calories']} ккал\n"
        f"🥩 Белки: {nutrition['protein']} г\n"
        f"🧈 Жиры: {nutrition['fat']} г\n"
        f"🍞 Углеводы: {nutrition['carbs']} г",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("confirm:"), FoodAddStates.entering_grams)
async def process_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    action = callback.data.split(":")[1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    if action == "edit":
        await callback.message.edit_text(
            "Введи новый вес порции в граммах:"
        )
        return

    data = await state.get_data()
    product = data["selected_product"]
    nutrition = data["nutrition"]
    meal_type = data["meal_type"]
    grams = data["grams"]

    entry = FoodLog(
        telegram_id=callback.from_user.id,
        log_date=date.today(),
        meal_type=meal_type,
        food_name=product["name"],
        amount_g=grams,
        calories=nutrition["calories"],
        protein=nutrition["protein"],
        fat=nutrition["fat"],
        carbs=nutrition["carbs"],
    )
    session.add(entry)
    await session.commit()
    await state.clear()

    meal_label = MEAL_TYPES[meal_type]
    save_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⭐ Сохранить блюдо", callback_data=f"save_meal:{entry.id}")
    ]])
    await callback.message.edit_text(
        f"✅ <b>Добавлено!</b>\n\n"
        f"{meal_label}: {product['name']} — {grams} г\n"
        f"🔥 +{nutrition['calories']} ккал\n\n"
        f"Посмотреть дневник: /today\n"
        f"Остаток: /left",
        reply_markup=save_kb,
        parse_mode="HTML"
    )
