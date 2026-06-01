from sqlalchemy import BigInteger, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from database import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    gender: Mapped[str | None] = mapped_column(String(6), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(10), nullable=True)

    daily_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_protein: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_fat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_carbs: Mapped[int | None] = mapped_column(Integer, nullable=True)

    timezone: Mapped[str] = mapped_column(String(40), default="Europe/Moscow")
    notify_morning: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_meals: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_evening: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_water: Mapped[bool] = mapped_column(Boolean, default=False)

    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_photo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
