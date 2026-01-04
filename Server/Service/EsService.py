import os, base64, re, json
from elasticsearch import Elasticsearch
from sqlalchemy import select
from Model.db_schema import TradeMark
from ..Config.db_config import get_db_session
from typing import List, Union, Dict
from ko_pron import romanise
import eng_to_ipa as ipa
from dotenv import load_dotenv
from ..PronunciationEvaluator.pronun import get_score
from redis import Redis

class EsService:
    def __init__(self, r: Redis):
        load_dotenv()
        username = os.environ['Elastic_Username']
        password = os.environ['Elastic_Password']
        credentials = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
        
        self.es = Elasticsearch(cloud_id=os.environ['Elastic_Cloud_ID'], 
                    basic_auth=(os.environ['Elastic_Username'], os.environ['Elastic_Password']))
        self.r = r
        self.header_ml = {"Content-Type": "application/json", 'Authorization': f'Basic {credentials}'}
        
    def queryForFindSameName(self, name: str) -> dict:
        try:
            with get_db_session() as session:
                stmt = select(TradeMark.name).where(TradeMark.WithoutSpaceName == name.replace(' ', ''))
                result = session.scalars(stmt).all()
            
            if result:
                return {"result": True, "msg": "\"" + result[0] +"\"이라는 같은 이름이 상표로 등록이 되어 있어 해당 명은 상표 등록이 불가능합니다."}
            else: 
                return {"result": False, "msg": ""}
        except Exception as e:
            return {"result": False, "msg": "error for FindSameName"}
        
        
    def queryForFindSimilarName(self, name: str) -> Dict[str, Union[bool, str, List[str]]]:
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
            resp_kr = self.es.search(index="tm_data", body={"query": query_kr})
            # 로마자 이름 검색 실행
            resp_eng = self.es.search(index="tm_data", body={"query": query_eng})

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
                return {"result": True, "data": SimilarNamesAndDates}
            else:
                return {"result": False, "msg": "유사한 이름을 찾을 수 없습니다."}
        except Exception as e:
            return {"result": False, "msg": "error for FindSimilarName"}
        
        
    def queryForFindSimilarPronun(self, name: str) -> Dict[str, Union[bool, str, List[str]]]:
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
            resp = self.es.search(index="tm_data", body=fuzzy_query)
            
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
                large_company_check = self.es.search(index='big_company', body=company_check_query)
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
            return {"result": False, "msg": "error for FindSimilarPronun"}
        
        
    def queryForCheckElastic(self, name: str) -> Dict[str, Union[bool, List[str]]]:
        try:
            resp = self.es.indices.analyze(
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
                redis_value = self.r.get(token)
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
            
            resp = self.es.transport.perform_request('POST', "/_ml/trained_models/matthewburke__korean_sentiment/deployment/_infer" ,body=json.dumps(req), headers= self.header_ml)

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
                    
                self.r.set(docs_list[i]["text_field"], json.dumps(redis_dict))
                    
            dedup_tokens = []
            for value in negative_token:
                if value not in dedup_tokens:
                    dedup_tokens.append(value)
            result = {"result": IsNegative, "NegativeTokens": dedup_tokens}
            
            return result
        except Exception as e:
            return {"result": False, "msg": 'error for checking positive/negative'}
