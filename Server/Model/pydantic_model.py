from pydantic import BaseModel

class TradeMarkModel(BaseModel):
    name: str
    item: str
