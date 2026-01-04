from sqlalchemy import select
from Model.db_schema import TradeMark

class TradeMarkDAO:
    def __init__(self, session):
        self.session = session
        
    def find_samename(self, name: str):
        stmt = select(TradeMark.name).where(TradeMark.WithoutSpaceName == name.replace(' ', ''))
        result = self.session.scalars(stmt).all()
        return result
