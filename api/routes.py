from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id, validate_init_data
from database import AsyncSessionLocal
from models.user import User
from models.food_log import FoodLog
from models.water_log import WaterLog
from models.weight_log import WeightLog
from models.user_food import UserFood
from services.food_api import search_food, calculate_portion
from services.stats import get_today_entries, get_daily_totals, get_week_data
from services.vision import analyze_food_photo
from services.calculator import calculate_targets
from config import MEAL_TYPES, ACTIVITY_LEVELS, GOAL_ADJUSTMENTS

router = APIRouter(prefix="/api")


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


async def get_user(telegram_id: int, session: AsyncSession) -> User:
    user = await session.get(User, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please start the bot first.")
    return user


# ── Schemas ───────────────────────────────────────────────────────────────────

class FoodAddRequest(BaseModel):
    food_name: str
    amount_g: float
    calories: float
    protein: float
    fat: float
    carbs: float
    meal_type: str
    log_date: Optional[str] = None


class WaterRequest(BaseModel):
    glasses: int


class WeightRequest(BaseModel):
    weight_kg: float


class PhotoConfirmRequest(BaseModel):
    food_name: str
    amount_g: float
    calories: float
    protein: float
    fat: float
    carbs: float
    meal_type: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    goal: Optional[str] = None


class ProfilePhotoRequest(BaseModel):
    photo: str  # base64 data URL: "data:image/jpeg;base64,..."


class UserFoodRequest(BaseModel):
    name: str
    kcal_100g: float
    protein_100g: float = 0.0
    fat_100g: float = 0.0
    carbs_100g: float = 0.0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    user = await get_user(telegram_id, session)
    return {
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "is_onboarded": user.is_onboarded,
        "goal": user.goal,
        "gender": user.gender,
        "activity_level": user.activity_level,
        "daily_calories": user.daily_calories,
        "daily_protein": user.daily_protein,
        "daily_fat": user.daily_fat,
        "daily_carbs": user.daily_carbs,
        "weight_kg": user.weight_kg,
        "height_cm": user.height_cm,
        "age": user.age,
        "profile_photo": user.profile_photo,
    }


@router.put("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    user = await get_user(telegram_id, session)

    if body.first_name is not None:
        user.first_name = body.first_name.strip()[:64]
    if body.age is not None:
        if not (10 <= body.age <= 120):
            raise HTTPException(status_code=400, detail="Age must be 10–120")
        user.age = body.age
    if body.height_cm is not None:
        if not (100 <= body.height_cm <= 250):
            raise HTTPException(status_code=400, detail="Height must be 100–250 cm")
        user.height_cm = body.height_cm
    if body.weight_kg is not None:
        if not (30 <= body.weight_kg <= 300):
            raise HTTPException(status_code=400, detail="Weight must be 30–300 kg")
        user.weight_kg = body.weight_kg
    if body.gender is not None:
        if body.gender not in ("male", "female"):
            raise HTTPException(status_code=400, detail="Gender must be male or female")
        user.gender = body.gender
    if body.activity_level is not None:
        if body.activity_level not in ACTIVITY_LEVELS:
            raise HTTPException(status_code=400, detail="Invalid activity_level")
        user.activity_level = body.activity_level
    if body.goal is not None:
        if body.goal not in GOAL_ADJUSTMENTS:
            raise HTTPException(status_code=400, detail="Invalid goal")
        user.goal = body.goal

    # Recalculate targets if we have all required fields
    if all([user.gender, user.age, user.height_cm, user.weight_kg, user.activity_level, user.goal]):
        targets = calculate_targets(
            user.gender, user.weight_kg, user.height_cm,
            user.age, user.activity_level, user.goal
        )
        user.daily_calories = targets["daily_calories"]
        user.daily_protein  = targets["daily_protein"]
        user.daily_fat      = targets["daily_fat"]
        user.daily_carbs    = targets["daily_carbs"]

    await session.commit()

    return {
        "ok": True,
        "daily_calories": user.daily_calories,
        "daily_protein":  user.daily_protein,
        "daily_fat":      user.daily_fat,
        "daily_carbs":    user.daily_carbs,
    }


@router.post("/profile/photo")
async def update_profile_photo(
    body: ProfilePhotoRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    if not body.photo.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid photo format")
    if len(body.photo) > 200_000:
        raise HTTPException(status_code=400, detail="Photo too large (max ~150KB)")
    user = await get_user(telegram_id, session)
    user.profile_photo = body.photo
    await session.commit()
    return {"ok": True}


@router.get("/today")
async def get_today(
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    user = await get_user(telegram_id, session)
    today = date.today()
    entries = await get_today_entries(session, telegram_id, today)
    totals = await get_daily_totals(session, telegram_id, today)

    result = await session.execute(
        select(WaterLog).where(
            WaterLog.telegram_id == telegram_id,
            WaterLog.log_date == today,
        )
    )
    water = result.scalar_one_or_none()

    return {
        "date": today.isoformat(),
        "entries": [
            {
                "id": e.id,
                "meal_type": e.meal_type,
                "meal_label": MEAL_TYPES.get(e.meal_type, e.meal_type),
                "food_name": e.food_name,
                "amount_g": e.amount_g,
                "calories": e.calories,
                "protein": e.protein,
                "fat": e.fat,
                "carbs": e.carbs,
            }
            for e in entries
        ],
        "totals": totals,
        "limits": {
            "calories": user.daily_calories,
            "protein": user.daily_protein,
            "fat": user.daily_fat,
            "carbs": user.daily_carbs,
        },
        "water_glasses": water.glasses if water else 0,
    }


@router.get("/food/search")
async def food_search(
    q: str = Query(..., min_length=2),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    user_foods_list = []
    user_data = validate_init_data(x_init_data) if x_init_data else None
    if user_data and user_data.get("id"):
        telegram_id = int(user_data["id"])
        result = await session.execute(
            select(UserFood).where(UserFood.telegram_id == telegram_id)
        )
        user_foods_list = [
            {
                "name": f.name,
                "kcal_100g": f.kcal_100g,
                "protein_100g": f.protein_100g,
                "fat_100g": f.fat_100g,
                "carbs_100g": f.carbs_100g,
                "user_food_id": f.id,
            }
            for f in result.scalars().all()
            if q.lower() in f.name.lower()
        ][:5]

    general = await search_food(q)
    return {"products": user_foods_list + general}


# ── USER FOODS (personal database) ───────────────────────────────────────────

@router.get("/user-foods")
async def list_user_foods(
    q: Optional[str] = Query(None),
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UserFood).where(UserFood.telegram_id == telegram_id).order_by(UserFood.name)
    )
    foods = result.scalars().all()
    if q:
        q_lower = q.lower()
        foods = [f for f in foods if q_lower in f.name.lower()]
    return {"foods": [_food_dict(f) for f in foods]}


@router.post("/user-foods")
async def create_user_food(
    body: UserFoodRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    _validate_food_values(body)
    name = body.name.strip()[:200]
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    existing = await session.execute(
        select(UserFood).where(
            UserFood.telegram_id == telegram_id,
            UserFood.name.ilike(name),
        )
    )
    dup = existing.scalar_one_or_none()
    if dup:
        return {"ok": False, "duplicate": True, "id": dup.id, "name": dup.name}

    food = UserFood(
        telegram_id=telegram_id,
        name=name,
        kcal_100g=round(body.kcal_100g, 1),
        protein_100g=round(body.protein_100g, 1),
        fat_100g=round(body.fat_100g, 1),
        carbs_100g=round(body.carbs_100g, 1),
    )
    session.add(food)
    await session.commit()
    await session.refresh(food)
    return {"ok": True, "id": food.id}


@router.put("/user-foods/{food_id}")
async def update_user_food(
    food_id: int,
    body: UserFoodRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    _validate_food_values(body)
    food = await session.get(UserFood, food_id)
    if not food or food.telegram_id != telegram_id:
        raise HTTPException(status_code=404, detail="Food not found")
    name = body.name.strip()[:200]
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    food.name = name
    food.kcal_100g = round(body.kcal_100g, 1)
    food.protein_100g = round(body.protein_100g, 1)
    food.fat_100g = round(body.fat_100g, 1)
    food.carbs_100g = round(body.carbs_100g, 1)
    food.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True, "food": _food_dict(food)}


@router.delete("/user-foods/{food_id}")
async def delete_user_food(
    food_id: int,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    food = await session.get(UserFood, food_id)
    if not food or food.telegram_id != telegram_id:
        raise HTTPException(status_code=404, detail="Food not found")
    await session.delete(food)
    await session.commit()
    return {"ok": True}


def _food_dict(f: UserFood) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "kcal_100g": f.kcal_100g,
        "protein_100g": f.protein_100g,
        "fat_100g": f.fat_100g,
        "carbs_100g": f.carbs_100g,
    }


def _validate_food_values(body: UserFoodRequest):
    if body.kcal_100g < 0 or body.protein_100g < 0 or body.fat_100g < 0 or body.carbs_100g < 0:
        raise HTTPException(status_code=400, detail="Values cannot be negative")


@router.post("/food/add")
async def food_add(
    body: FoodAddRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    await get_user(telegram_id, session)

    if body.meal_type not in MEAL_TYPES:
        raise HTTPException(status_code=400, detail="Invalid meal_type")

    log_date = date.fromisoformat(body.log_date) if body.log_date else date.today()

    entry = FoodLog(
        telegram_id=telegram_id,
        log_date=log_date,
        meal_type=body.meal_type,
        food_name=body.food_name[:200],
        amount_g=body.amount_g,
        calories=body.calories,
        protein=body.protein,
        fat=body.fat,
        carbs=body.carbs,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return {"id": entry.id, "ok": True}


@router.post("/food/photo")
async def food_photo(
    photo: UploadFile = File(...),
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    await get_user(telegram_id, session)
    image_bytes = await photo.read()
    result = await analyze_food_photo(image_bytes)

    if result is None or "error" in result:
        error = result.get("error", "unknown") if result else "unknown"
        if error == "not_food":
            raise HTTPException(status_code=422, detail="not_food")
        if error == "no_key":
            raise HTTPException(status_code=503, detail="AI not configured")
        raise HTTPException(status_code=500, detail=f"AI error: {error}")

    return result


@router.delete("/food/{entry_id}")
async def food_delete(
    entry_id: int,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    entry = await session.get(FoodLog, entry_id)
    if not entry or entry.telegram_id != telegram_id:
        raise HTTPException(status_code=404, detail="Entry not found")
    await session.delete(entry)
    await session.commit()
    return {"ok": True}


@router.get("/stats/week")
async def stats_week(
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    await get_user(telegram_id, session)
    week = await get_week_data(session, telegram_id)
    return {
        "days": [
            {**d, "date": d["date"].isoformat()}
            for d in week
        ]
    }


@router.get("/water")
async def water_get(
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    today = date.today()
    result = await session.execute(
        select(WaterLog).where(
            WaterLog.telegram_id == telegram_id,
            WaterLog.log_date == today,
        )
    )
    water = result.scalar_one_or_none()
    return {"glasses": water.glasses if water else 0, "date": today.isoformat()}


@router.post("/water")
async def water_add(
    body: WaterRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    today = date.today()
    result = await session.execute(
        select(WaterLog).where(
            WaterLog.telegram_id == telegram_id,
            WaterLog.log_date == today,
        )
    )
    water = result.scalar_one_or_none()
    if water:
        water.glasses = max(0, water.glasses + body.glasses)
    else:
        water = WaterLog(telegram_id=telegram_id, log_date=today, glasses=max(0, body.glasses))
        session.add(water)
    await session.commit()
    return {"glasses": water.glasses, "ok": True}


@router.post("/weight")
async def weight_log(
    body: WeightRequest,
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    entry = WeightLog(
        telegram_id=telegram_id,
        log_date=date.today(),
        weight_kg=body.weight_kg,
    )
    session.add(entry)
    await session.commit()
    return {"ok": True}


@router.get("/weight/history")
async def weight_history(
    telegram_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WeightLog)
        .where(WeightLog.telegram_id == telegram_id)
        .order_by(WeightLog.log_date.desc())
        .limit(30)
    )
    entries = result.scalars().all()
    return {
        "entries": [
            {"date": e.log_date.isoformat(), "weight_kg": e.weight_kg}
            for e in entries
        ]
    }
