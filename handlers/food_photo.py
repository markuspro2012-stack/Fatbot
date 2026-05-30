from datetime import date
import io

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.food_log import FoodLog
from services.vision import analyze_food_photo
from services.food_api import search_food, calculate_portion
from config import MEAL_TYPES

router = Router()


class PhotoAddStates(StatesGroup):
    confirming = State()
    editing_grams = State()
    editing_name = State()
    selecting_meal = State()
    searching_manual = State()
    choosing_manual = State()
    entering_manual_grams = State()


def confidence_emoji(confidence: str) -> str:
    return {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "🟡")


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Верно, выбрать приём пищи", callback_data="photo:select_meal")],
        [
            InlineKeyboardButton(text="✏️ Изменить граммы", callback_data="photo:edit_grams"),
            InlineKeyboardButton(text="📝 Изменить название", callback_data="photo:edit_name"),
        ],
        [InlineKeyboardButton(text="🔍 Искать вручную", callback_data="photo:search_manual")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="photo:cancel")],
    ])


def meal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 Завтрак", callback_data="photomeal:breakfast"),
            InlineKeyboardButton(text="☀️ Обед", callback_data="photomeal:lunch"),
        ],
        [
            InlineKeyboardButton(text="🌙 Ужин", callback_data="photomeal:dinner"),
            InlineKeyboardButton(text="🍎 Перекус", callback_data="photomeal:snack"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="photomeal:cancel")],
    ])


def manual_results_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for i, p in enumerate(products):
        label = f"{p['name'][:35]} · {p['kcal_100g']} ккал/100г"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"photoproduct:{i}")])
    buttons.append([InlineKeyboardButton(text="🔍 Искать заново", callback_data="photoproduct:retry")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="photoproduct:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def result_text(data: dict) -> str:
    conf = confidence_emoji(data.get("confidence", "medium"))
    return (
        f"🤖 <b>Распознано:</b> {data['food_name']} {conf}\n\n"
        f"⚖️ Вес порции: <b>{int(data['amount_g'])} г</b>\n"
        f"🔥 Калории: <b>{data['calories']} ккал</b>\n"
        f"🥩 Белки: <b>{data['protein']} г</b>\n"
        f"🧈 Жиры: <b>{data['fat']} г</b>\n"
        f"🍞 Углеводы: <b>{data['carbs']} г</b>\n\n"
        f"Всё верно?"
    )


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    user = await session.get(User, message.from_user.id)
    if not user or not user.is_onboarded:
        await message.answer("Сначала настрой профиль: /setup")
        return

    await state.clear()
    status_msg = await message.answer("🔍 Анализирую фото, подожди секунду...")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path, destination=buf)
    image_bytes = buf.getvalue()

    result = await analyze_food_photo(image_bytes)

    if result is None or "error" in result:
        error = result.get("error", "unknown") if result else "unknown"
        if error == "no_key":
            await status_msg.edit_text(
                "📸 Распознавание фото не настроено (нет Gemini API ключа).\n\n"
                "Добавь еду вручную: /add"
            )
        elif error == "not_food":
            await status_msg.edit_text(
                "😕 На фото не распознана еда.\n\n"
                "Попробуй другое фото или добавь вручную: /add"
            )
        else:
            await status_msg.edit_text(
                "⚠️ Не удалось обработать фото. Попробуй ещё раз или добавь вручную: /add"
            )
        return

    await state.update_data(vision_result=result)
    await state.set_state(PhotoAddStates.confirming)

    await status_msg.edit_text(
        result_text(result),
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "photo:cancel", PhotoAddStates.confirming)
async def photo_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено. Отправь фото снова или /add чтобы добавить вручную.")


# ── Редактирование граммов ────────────────────────────────────────────────────

@router.callback_query(F.data == "photo:edit_grams", PhotoAddStates.confirming)
async def photo_edit_grams(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PhotoAddStates.editing_grams)
    data = await state.get_data()
    result = data["vision_result"]
    await callback.message.edit_text(
        f"Текущий вес: <b>{int(result['amount_g'])} г</b>\n\n"
        "Введи правильный вес порции в граммах:",
        parse_mode="HTML"
    )


@router.message(PhotoAddStates.editing_grams)
async def photo_process_new_grams(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введи вес цифрами, например: <code>200</code>", parse_mode="HTML")
        return
    try:
        grams = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи вес цифрами, например: <code>200</code>", parse_mode="HTML")
        return
    if not (1 <= grams <= 5000):
        await message.answer("Введи реальный вес от 1 до 5000 г.")
        return

    data = await state.get_data()
    result = data["vision_result"]

    ratio = grams / result["amount_g"]
    result["amount_g"] = grams
    result["calories"] = round(result["calories"] * ratio, 1)
    result["protein"] = round(result["protein"] * ratio, 1)
    result["fat"] = round(result["fat"] * ratio, 1)
    result["carbs"] = round(result["carbs"] * ratio, 1)

    await state.update_data(vision_result=result)
    await state.set_state(PhotoAddStates.confirming)

    await message.answer(
        result_text(result),
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


# ── Редактирование названия ───────────────────────────────────────────────────

@router.callback_query(F.data == "photo:edit_name", PhotoAddStates.confirming)
async def photo_edit_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PhotoAddStates.editing_name)
    data = await state.get_data()
    result = data["vision_result"]
    await callback.message.edit_text(
        f"Текущее название: <b>{result['food_name']}</b>\n\n"
        "Введи правильное название блюда:",
        parse_mode="HTML"
    )


@router.message(PhotoAddStates.editing_name)
async def photo_process_new_name(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Введи название блюда:")
        return

    data = await state.get_data()
    result = data["vision_result"]
    result["food_name"] = message.text.strip()[:100]

    await state.update_data(vision_result=result)
    await state.set_state(PhotoAddStates.confirming)

    await message.answer(
        result_text(result),
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


# ── Ручной поиск если фото не то ─────────────────────────────────────────────

@router.callback_query(F.data == "photo:search_manual", PhotoAddStates.confirming)
async def photo_search_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PhotoAddStates.searching_manual)
    await callback.message.edit_text(
        "🔍 Поиск в базе продуктов\n\n"
        "Напиши название продукта или блюда:\n"
        "<i>Например: куриная грудка, гречка, творог</i>",
        parse_mode="HTML"
    )


@router.message(PhotoAddStates.searching_manual)
async def photo_process_manual_search(message: Message, state: FSMContext):
    query = message.text.strip() if message.text else ""
    if not query:
        await message.answer("Введи название продукта:")
        return

    searching_msg = await message.answer("🔍 Ищу в базе продуктов...")
    products = await search_food(query)

    if not products:
        await searching_msg.edit_text(
            f"😕 По запросу «{query}» ничего не найдено.\n\n"
            "Попробуй другое название (на английском тоже работает):"
        )
        return

    await state.update_data(manual_search_results=products)
    await state.set_state(PhotoAddStates.choosing_manual)

    await searching_msg.edit_text(
        f"Нашёл по запросу «{query}»:\n\nВыбери продукт:",
        reply_markup=manual_results_keyboard(products)
    )


@router.callback_query(F.data.startswith("photoproduct:"), PhotoAddStates.choosing_manual)
async def photo_choose_manual_product(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    if action == "retry":
        await state.set_state(PhotoAddStates.searching_manual)
        await callback.message.edit_text("Введи другое название продукта:")
        return

    idx = int(action)
    data = await state.get_data()
    products = data["manual_search_results"]
    product = products[idx]

    await state.update_data(manual_product=product)
    await state.set_state(PhotoAddStates.entering_manual_grams)

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


@router.message(PhotoAddStates.entering_manual_grams)
async def photo_manual_grams(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введи вес в граммах, например: <code>150</code>", parse_mode="HTML")
        return
    try:
        grams = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи вес цифрами, например: <code>150</code>", parse_mode="HTML")
        return
    if not (1 <= grams <= 5000):
        await message.answer("Введи реальный вес от 1 до 5000 г.")
        return

    data = await state.get_data()
    product = data["manual_product"]
    nutrition = calculate_portion(product, grams)

    result = {
        "food_name": product["name"],
        "amount_g": grams,
        "calories": nutrition["calories"],
        "protein": nutrition["protein"],
        "fat": nutrition["fat"],
        "carbs": nutrition["carbs"],
        "confidence": "high",
        "from_manual": True,
    }

    await state.update_data(vision_result=result)
    await state.set_state(PhotoAddStates.confirming)

    await message.answer(
        result_text(result),
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


# ── Выбор приёма пищи и сохранение ───────────────────────────────────────────

@router.callback_query(F.data == "photo:select_meal", PhotoAddStates.confirming)
async def photo_select_meal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PhotoAddStates.selecting_meal)
    await callback.message.edit_text(
        "Выбери тип приёма пищи:",
        reply_markup=meal_keyboard()
    )


@router.callback_query(F.data.startswith("photomeal:"), PhotoAddStates.selecting_meal)
async def photo_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    meal_type = callback.data.split(":")[1]

    if meal_type == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    data = await state.get_data()
    result = data["vision_result"]

    entry = FoodLog(
        telegram_id=callback.from_user.id,
        log_date=date.today(),
        meal_type=meal_type,
        food_name=result["food_name"],
        amount_g=result["amount_g"],
        calories=result["calories"],
        protein=result["protein"],
        fat=result["fat"],
        carbs=result["carbs"],
    )
    session.add(entry)
    await session.commit()
    await state.clear()

    meal_label = MEAL_TYPES[meal_type]
    save_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⭐ Сохранить как избранное", callback_data=f"save_meal:{entry.id}")
    ]])
    await callback.message.edit_text(
        f"✅ <b>Добавлено!</b>\n\n"
        f"{meal_label}: {result['food_name']} — {int(result['amount_g'])} г\n"
        f"🔥 +{result['calories']} ккал\n\n"
        f"Посмотреть дневник: /today\n"
        f"Остаток: /left",
        reply_markup=save_kb,
        parse_mode="HTML"
    )
