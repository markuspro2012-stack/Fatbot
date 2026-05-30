from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.food_log import FoodLog


async def get_today_entries(session: AsyncSession, telegram_id: int, today: date) -> list[FoodLog]:
    result = await session.execute(
        select(FoodLog)
        .where(FoodLog.telegram_id == telegram_id, FoodLog.log_date == today)
        .order_by(FoodLog.added_at)
    )
    return list(result.scalars().all())


async def get_daily_totals(session: AsyncSession, telegram_id: int, log_date: date) -> dict:
    result = await session.execute(
        select(
            func.coalesce(func.sum(FoodLog.calories), 0),
            func.coalesce(func.sum(FoodLog.protein), 0),
            func.coalesce(func.sum(FoodLog.fat), 0),
            func.coalesce(func.sum(FoodLog.carbs), 0),
        ).where(FoodLog.telegram_id == telegram_id, FoodLog.log_date == log_date)
    )
    row = result.one()
    return {
        "calories": round(row[0], 1),
        "protein": round(row[1], 1),
        "fat": round(row[2], 1),
        "carbs": round(row[3], 1),
    }


async def get_week_data(session: AsyncSession, telegram_id: int) -> list[dict]:
    today = date.today()
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        totals = await get_daily_totals(session, telegram_id, d)
        days.append({"date": d, **totals})
    return days


def progress_bar(current: float, limit: float, width: int = 10) -> str:
    if limit <= 0:
        return "░" * width
    ratio = min(current / limit, 1.0)
    filled = round(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    percent = round(ratio * 100)
    return f"{bar} {percent}%"
