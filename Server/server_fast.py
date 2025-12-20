import dotenv, os, json, base64, re, fasttext, asyncio
from elasticsearch import Elasticsearch
from sqlalchemy import select
from db_schema import TradeMark
from db_config import SessionLocal
from ko_pron import romanise
from typing import List, Union, Dict
from redis import Redis
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
import numpy as np
import pandas as pd
import eng_to_ipa as ipa
from ..PronunciationEvaluator.pronun import get_score

@asynccontextmanager
async def lifespan(app: FastAPI):
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    username = os.environ['Elastic_Username']
    password = os.environ['Elastic_Password']
    credentials = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
    
    app.state.es = Elasticsearch(cloud_id=os.environ['Elastic_Cloud_ID'], 
                       basic_auth= (os.environ['Elastic_Username'], os.environ['Elastic_Password']))
    app.state.redis = Redis(host='localhost', port=6379, db=0)
    app.state.model = fasttext.load_model('kor.bin')
    app.state.header_ml = {"Content-Type": "application/json", 'Authorization': f'Basic {credentials}'}
    
app = FastAPI(lifespan=lifespan)

# dependency func
def get_es() -> Elasticsearch:
    return app.state.es

def get_redis() -> Redis:
    return app.state.redis

def get_header() -> dict:
    return app.state.header_ml

def calculate_similarity(model, trademark_name: str, product_name: str):
    refined_name = trademark_name.replace(product_name, "").strip()
    vector1 = model.get_sentence_vector(refined_name)
    vector2 = model.get_sentence_vector(product_name)
    similarity = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
    
    if np.isnan(similarity):
        similarity = 0
        
    return similarity

# for main func
def queryForFindSameName(name: str, 
                        es: Elasticsearch) -> dict:
    try:
        with SessionLocal() as session:
            stmt = select(TradeMark.name).where(TradeMark.WithoutSpaceName == name.replace(' ', ''))
            result = session.scalars(stmt).all()
        
        if result:
            ret = {"result": True, "msg": "\"" + result[0] +"\"이라는 같은 이름이 상표로 등록이 되어 있어 해당 명은 상표 등록이 불가능합니다."}
            return ret 
        else: 
            ret = {"result": False, "msg": ""}
            return ret
    except Exception as e:
        return {"result": False, "msg": "error for FindSameName"}
        
        
def queryForFindSimilarName(name: str,
                            es: Elasticsearch) -> Dict[str, Union[bool, str, List[str]]]:
    try:
        # 한글 이름에서 공백 제거
        name = name.replace(' ', '')
        # 로마자 이름 변환
        eng_name = romanise(name, "rr")

        # 한글 이름에 대한 퍼지 쿼리
        query_kr = {
            "fuzzy": {
                "title": {
                    "value": name,
                    "fuzziness": "2"
                }
            }
        }

        # 로마자 이름에 대한 퍼지 쿼리
        query_eng = {
            "fuzzy": {
                "eng_title": {
                    "value": eng_name,
                    "fuzziness": "2"
                }
            }
        }

        # 한글 이름 검색 실행
        resp_kr = es.search(index="tm_data", body={"query": query_kr})
        # 로마자 이름 검색 실행
        resp_eng = es.search(index="tm_data", body={"query": query_eng})

        IsSimilar = False
        SimilarNamesAndDates = []

        # 로마자 이름 검색 결과 처리
        for ans in resp_eng["hits"]["hits"]:
            similar_title = ans["_source"]["title"]
            application_date = ans["_source"].get("applicationDate", "출원일 정보 없음")
            image_url = ans["_source"].get("bigDrawing", None)
            SimilarNamesAndDates.append((similar_title, application_date, image_url))
            IsSimilar = True

        # 한글 이름 검색 결과 처리
        for ans in resp_kr["hits"]["hits"]:
            similar_title = ans["_source"]["title"]
            application_date = ans["_source"].get("applicationDate", "출원일 정보 없음")
            image_url = ans["_source"].get("bigDrawing", None)
            SimilarNamesAndDates.append((similar_title, application_date, image_url))
            IsSimilar = True

        if IsSimilar:
            ret = {"result": True, "data": SimilarNamesAndDates}
            return ret
        else:
            ret = {"result": False, "msg": "유사한 이름을 찾을 수 없습니다."}
            return ret

    except Exception as e:
        return {"result": False, "msg": "error for FindSimilarName"}
    
def queryForFindSimilarPronun(name: str, es: Elasticsearch) -> Dict[str, Union[bool, str, List[str]]]:
    try:
        # Convert name to IPA
        segments = re.split('([가-힣]+)', name)
        ipa_name = ""
        for segment in segments:
            if segment and re.match('[가-힣]+', segment):
                ipa_name += romanise(segment, "ipa")
            else:
                ipa_name += ipa.convert(segment)
        
        # Fuzzy query on ipa_title
        fuzzy_query = {
            "query": {
                "fuzzy": {
                    "ipa_title": {
                        "value": ipa_name,
                        "fuzziness": "2"
                    }
                }
            }
        }
        resp = es.search(index="tm_data", body=fuzzy_query)
        
        SimilarNamesWithScores = []
        
        # For each similar title found
        for ans in resp['hits']['hits']:
            title = ans['_source']['title']
            score = get_score(ipa_name, ans['_source']['ipa_title'])
            application_date = ans['_source'].get('applicationDate', '출원일 정보 없음')
            image_url = ans['_source'].get('bigDrawing', None)

            company_check_query = {
                "query": {
                    "match": {
                        "column3": title
                    }
                }
            }
            large_company_check = es.search(index='big_company', body=company_check_query)
            is_large_company = large_company_check['hits']['total']['value'] > 0
            
            # Adjust similarity score threshold based on company size
            if is_large_company and score['score'] > 0.55 or not is_large_company and score['score'] > 0.7:
                company_label = " (대형 기업)" if is_large_company else ""
                SimilarNamesWithScores.append((f"{title}{company_label}", score['score'], application_date, image_url))
        
        # Sort by similarity score
        SimilarNamesWithScores.sort(key=lambda x: x[1], reverse=True)
        
        if SimilarNamesWithScores:
            return {"result": True, "data": SimilarNamesWithScores}
        else:
            return {"result": False, "msg": "유사한 상표명 없음"}
    except Exception as e:
        print('Error in queryForFindSimilarPronun:', e)
        return {"result": False, "msg": "error for FindSimilarPronun"}

def queryForCheckElastic(name: str, es: Elasticsearch, r: Redis, header) -> Dict[str, Union[bool, List[str]]]:
    try:
        resp = es.indices.analyze(
            body= {
                "tokenizer": "nori_tokenizer",
                "text": name
            }
        )
        
        IsNegative = False
        negative_token = []
        docs_list = []
        
        for token in resp["tokens"]["token"]:
            # redis- key:token, value: state, positive probability, negative probability
            redis_value = r.get(token)
            if redis_value is not None: # redis에 있음
                redis_value = json.loads(redis_value)
                
                if redis_value['state'] == 'negative':
                    IsNegative = True
                    negative_token.append({"name": token,
                                        "positive": redis_value['positive_prob'], 
                                        "negative": redis_value['negative_prob']})
            else:
                docs_list.append({"text_field": token})
          
        req = {
            "docs": docs_list,

            "inference_config": {
                "text_classification": {
                    "num_top_classes": 2
                    }
                }
        }
        
        resp = es.transport.perform_request('POST', "/_ml/trained_models/matthewburke__korean_sentiment/deployment/_infer" ,body=json.dumps(req), headers= header)

        for i in range(len(resp.body)):
            if resp.body[i]["top_classes"][0]["class_name"] == "LABEL_0" and resp.body[i]["top_classes"][0]["class_score"] > 0.8:
                IsNegative = True
                redis_dict = {'state': 'negative',
                            'positive_prob': resp.body[i]["top_classes"][1]["class_score"],
                            'negative_prob': resp.body[i]["top_classes"][0]["class_score"] }
                
                negative_token.append({"name": docs_list[i]["text_field"],
                                "positive": resp.body[i]["top_classes"][1]["class_score"], 
                                "negative": resp.body[i]["top_classes"][0]["class_score"]})
            else:
                redis_dict = {'state': 'positive',
                            'positive_prob': resp.body[i]["top_classes"][1]["class_score"],
                            'negative_prob': resp.body[i]["top_classes"][0]["class_score"] }
                
            r.set(docs_list[i]["text_field"], json.dumps(redis_dict))
                
        dedup_tokens = []
        for value in negative_token:
            if value not in dedup_tokens:
                dedup_tokens.append(value)
        result = {"result": IsNegative, "NegativeTokens": dedup_tokens}
        
        return result
    except Exception as e:
        return {"result": False, "msg": 'error for checking positive/negative'}
    
@app.get("/search")
async def search_trademark(name: str,
                        es = Depends(get_es),
                        r = Depends(get_redis), 
                        header_ml = Depends(get_header)):
    try:
        task1 = asyncio.to_thread(queryForFindSameName, name, es)
        task2 = asyncio.to_thread(queryForFindSimilarName, name, es)
        task3 = asyncio.to_thread(queryForFindSimilarPronun, name, es)
        task4 = asyncio.to_thread(queryForCheckElastic, name, es, r, header_ml)
        results = await asyncio.gather(task1, task2, task3, task4)
        return {"samename_result": results[0], 
                "similar_result": results[1],
                "similarpronun_result": results[2],
                "ml_result": results[3]}
    except Exception as e:
        return {"status": "error", "message": str(e)} 
