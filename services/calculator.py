from config import ACTIVITY_LEVELS, GOAL_ADJUSTMENTS


def calculate_bmr(gender: str, weight_kg: float, height_cm: int, age: int) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "male" else base - 161


def calculate_targets(gender: str, weight_kg: float, height_cm: int, age: int,
                       activity_level: str, goal: str) -> dict:
    bmr = calculate_bmr(gender, weight_kg, height_cm, age)
    tdee = bmr * ACTIVITY_LEVELS[activity_level]
    daily_calories = round(tdee + GOAL_ADJUSTMENTS[goal])

    daily_calories = max(1200 if gender == "female" else 1500, daily_calories)

    protein = round(weight_kg * 2)
    fat = round(daily_calories * 0.25 / 9)
    carbs = round((daily_calories - protein * 4 - fat * 9) / 4)

    return {
        "daily_calories": daily_calories,
        "daily_protein": protein,
        "daily_fat": fat,
        "daily_carbs": carbs,
        "bmr": round(bmr),
        "tdee": round(tdee),
    }


def format_profile_text(user) -> str:
    from config import ACTIVITY_LABELS, GOAL_LABELS
    gender_label = "Мужской" if user.gender == "male" else "Женский"
    activity_label = ACTIVITY_LABELS.get(user.activity_level, user.activity_level)
    goal_label = GOAL_LABELS.get(user.goal, user.goal)

    return (
        f"👤 <b>Твой профиль</b>\n\n"
        f"Пол: {gender_label}\n"
        f"Возраст: {user.age} лет\n"
        f"Рост: {user.height_cm} см\n"
        f"Вес: {user.weight_kg} кг\n"
        f"Активность: {activity_label}\n"
        f"Цель: {goal_label}\n\n"
        f"📊 <b>Дневные лимиты</b>\n\n"
        f"🔥 Калории: <b>{user.daily_calories} ккал</b>\n"
        f"🥩 Белки: <b>{user.daily_protein} г</b>\n"
        f"🧈 Жиры: <b>{user.daily_fat} г</b>\n"
        f"🍞 Углеводы: <b>{user.daily_carbs} г</b>\n\n"
        f"Хочешь изменить данные? /setup"
    )
