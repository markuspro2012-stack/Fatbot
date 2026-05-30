import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
DATABASE_URL: str = os.environ["DATABASE_URL"]

ACTIVITY_LEVELS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

ACTIVITY_LABELS = {
    "sedentary": "Сидячий (офис, без спорта)",
    "light": "Лёгкий (1-2 тренировки в неделю)",
    "moderate": "Умеренный (3-5 тренировок в неделю)",
    "active": "Активный (6-7 тренировок в неделю)",
    "very_active": "Очень активный (спорт каждый день + физический труд)",
}

GOAL_LABELS = {
    "lose": "Похудеть",
    "maintain": "Поддерживать вес",
    "gain": "Набрать массу",
}

GOAL_ADJUSTMENTS = {
    "lose": -500,
    "maintain": 0,
    "gain": 300,
}

MEAL_TYPES = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
}
