from sqlalchemy import BigInteger, String, Integer, Float, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from database import Base


class FoodLog(Base):
    __tablename__ = "food_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    log_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))

    food_name: Mapped[str] = mapped_column(String(200))
    amount_g: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    protein: Mapped[float] = mapped_column(Float, default=0)
    fat: Mapped[float] = mapped_column(Float, default=0)
    carbs: Mapped[float] = mapped_column(Float, default=0)

    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
