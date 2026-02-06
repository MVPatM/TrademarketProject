from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TradeMark(Base):
    __tablename__ = "trademark"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tradeMarkName: Mapped[str] = mapped_column(String(50))
    ipa_name: Mapped[str] = mapped_column(String(100))
    eng_name: Mapped[str] = mapped_column(String(100))
    registrationDate: Mapped[datetime] = mapped_column(DateTime)
    isLargeCompany: Mapped[bool] = mapped_column(Boolean)
