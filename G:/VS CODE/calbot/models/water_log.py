from sqlalchemy import BigInteger, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from database import Base


class WaterLog(Base):
    __tablename__ = "water_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    log_date: Mapped[date] = mapped_column(Date)
    glasses: Mapped[int] = mapped_column(Integer, default=0)
