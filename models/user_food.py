from sqlalchemy import BigInteger, String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from database import Base


class UserFood(Base):
    __tablename__ = "user_foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kcal_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
