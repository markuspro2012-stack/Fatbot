from sqlalchemy import BigInteger, Float, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from database import Base


class WeightLog(Base):
    __tablename__ = "weight_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    log_date: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Float)
