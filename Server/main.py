import asyncio, os
from typing import List, Union, Dict
from redis import Redis
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from Service.EsService import EsService
from Service.FastTextService import FastTextService
from Model.pydantic_model import TradeMarkModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()

    r = Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], db=os.environ['REDIS_DB'])
    app.state.es = EsService(r)
    app.state.redis = r
    app.state.model = FastTextService()
    
app = FastAPI(lifespan=lifespan)

# dependency func
def get_es() -> EsService:
    return app.state.es

def get_redis() -> Redis:
    return app.state.redis

def get_model() -> FastTextService:
    return app.state.model

# for main func
def queryForFindSameName(name: str, es: EsService) -> dict:
    return es.queryForFindSameName(name)
        
def queryForFindSimilarName(name: str, es: EsService) -> Dict[str, Union[bool, str, List[str]]]:
    return es.queryForFindSimilarName(name)
    
def queryForFindSimilarPronun(name: str, es: EsService) -> Dict[str, Union[bool, str, List[str]]]:
    return es.queryForFindSimilarPronun(name)

def queryForCheckElastic(name: str, es: EsService) -> Dict[str, Union[bool, List[str]]]:
    return es.queryForCheckElastic(name)

def getSimilarity(name: str, item: str, model: FastTextService):
    return model.getSimilarity(name, item)

@app.get("/search")
async def search_trademark(trademark: TradeMarkModel,
                        es = Depends(get_es)):
    try:
        task1 = asyncio.to_thread(queryForFindSameName, trademark.name, es)
        task2 = asyncio.to_thread(queryForFindSimilarName, trademark.name, es)
        task3 = asyncio.to_thread(queryForFindSimilarPronun, trademark.name, es)
        task4 = asyncio.to_thread(queryForCheckElastic, trademark.name, es)
        task5 = asyncio.to_thread(getSimilarity, trademark.name, trademark.item)
        results = await asyncio.gather(task1, task2, task3, task4, task5)
        return {"samename_result": results[0], 
                "similar_result": results[1],
                "similarpronun_result": results[2],
                "ml_result": results[3],
                "similarity_result": results[4]}
    except Exception as e:
        return {"status": "error", "message": str(e)} 
