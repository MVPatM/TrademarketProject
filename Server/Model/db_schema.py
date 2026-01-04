from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TradeMark(Base):
    __tablename__ = "trademark"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tradeMarkName: Mapped[str] = mapped_column(String(50))
    registrationDate: Mapped[datetime] = mapped_column(DateTime)
    WithoutSpaceName: Mapped[str] = mapped_column(String(50))
