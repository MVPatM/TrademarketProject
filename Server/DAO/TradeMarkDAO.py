from sqlalchemy import select, func, and_
from Model.db_schema import TradeMark
from Config.db_config import get_db_session

class TradeMarkDAO:
    def find_samename(self, name: str):
        with get_db_session() as session:
            stmt = select(TradeMark.tradeMarkName).where(func.replace(TradeMark.tradeMarkName, ' ', '') == name.replace(' ', ''))
            result = session.scalars(stmt).all()
            return result
        
    def get_is_large_company_info(self, name: str):
        with get_db_session() as session:
            stmt = select(TradeMark.isLargeCompany).where(TradeMark.tradeMarkName == name)
            result = session.scalar(stmt)
            return result
    
    def find_names_by_levenshtein(self, name: str, threshold: int = 3):
        with get_db_session() as session:
            stmt = (select(TradeMark.tradeMarkName, TradeMark.registrationDate)
                    .where(
                        and_(
                            TradeMark.tradeMarkName.op('%')(name),
                            func.levenshtein(TradeMark.tradeMarkName, name) <= threshold)
                    ))
            result = session.execute(stmt).all()
            return result
            
    def find_eng_names_by_levenshtein(self, eng_name: str, threshold: int = 3):
        with get_db_session() as session:
            stmt = (select(TradeMark.tradeMarkName, TradeMark.registrationDate)
                    .where(
                        and_(
                            TradeMark.eng_name.op('%')(eng_name),
                            func.levenshtein(TradeMark.eng_name, eng_name) <= threshold)
                    ))
            result = session.execute(stmt).all()
            return result

    def find_names_by_ipa_levenshtein(self, ipa_name: str, threshold: int = 3):
        with get_db_session() as session:
            stmt = (select(TradeMark.tradeMarkName, TradeMark.ipa_name)
                    .where(
                        and_(
                            TradeMark.ipa_name.op('%')(ipa_name),
                            func.levenshtein(TradeMark.ipa_name, ipa_name) <= threshold)
                        )
                    )
            
            result = session.execute(stmt).all()
            return result
