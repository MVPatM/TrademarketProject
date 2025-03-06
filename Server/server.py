import streamlit as st 
import dotenv
import os
import re
import json
import numpy as np
import base64
import fasttext
import eng_to_ipa as ipa
import requests
import pandas as pd
import plotly.express as px
from PIL import Image
from io import BytesIO
from elasticsearch import Elasticsearch
from konlpy.tag import Okt
from ko_pron import romanise
from ..PronunciationEvaluator.pronun import get_score
import time
from typing import List, Union, Dict

@st.cache_resource
def connectToElastic() -> Elasticsearch:
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    es = Elasticsearch(cloud_id=os.environ['Elastic_Cloud_ID'], 
                       basic_auth= (os.environ['Elastic_Username'], os.environ['Elastic_Password']))

    return es

def download_and_show_image(image_url: str):
    if image_url:
        response = requests.get(image_url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            st.image(image)
        else:
            st.error("이미지를 다운로드할 수 없습니다.")
    else:
        st.info("이미지 URL이 제공되지 않았습니다.")
    
def queryForFindSameNameV2(name: str, es: Elasticsearch) -> Dict[str, Union[bool, str]]:
    try:
        name = name.replace(' ', '')
        query = {
            "match": {
                "title": name
            }
        }
        
        resp = es.search(index = 'tm_data_ngram', 
                  body = {"query": query, "size": 500})
        
        IsSame = False
        SameName = None
        name = name.lower()
        for ans in resp["hits"]["hits"]:
            cmp = ans["_source"]["title"].lower()
            if name == cmp.replace(' ', ''):
                SameName = ans["_source"]["title"]
                IsSame = True
                break
        
        if IsSame:
            ret = {"result": True, "msg": "\"" + SameName +"\"이라는 같은 이름이 상표로 등록이 되어 있어 해당 명은 상표 등록이 불가능합니다."}
            return ret 
        else:
            ret = {"result": False, "msg": ""}
            return ret
        
    except Exception as e:
        st.write("error for FindNameV2")
        
def queryForFindSimilarName(name: str, es: Elasticsearch) -> Dict[str, Union[bool, str, List[str]]]:
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
        print('Error in queryForFindSimilarName: ', str(e))
        return {"result": False, "msg": "오류 발생"}




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
        return {"result": False, "msg": "오류 발생"}



@st.cache_resource
def load_model():
    model = fasttext.load_model('kor.bin')
    return model

def calculate_similarity(model, trademark_name: str, product_name: str):
    refined_name = trademark_name.replace(product_name, "").strip()
    vector1 = model.get_sentence_vector(refined_name)
    vector2 = model.get_sentence_vector(product_name)
    similarity = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
    
    if np.isnan(similarity):
        similarity = 0
        
    return similarity

    
def Tokenize(name: str) -> List[str]:
    try:
        analyzer = Okt()
        tokens = analyzer.morphs(name)
        return tokens
    except Exception as e:
        st.write('error for tokenization')
    
def queryForCheckElastic(name: str, es: Elasticsearch) -> Dict[str, Union[bool, List[str]]]:
    try:
        dotenv_file = dotenv.find_dotenv()
        dotenv.load_dotenv(dotenv_file)
        
        username = os.environ['Elastic_Username']
        password = os.environ['Elastic_Password']
        credentials = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
        header = {"Content-Type": "application/json", 'Authorization': f'Basic {credentials}'}
        
        tokens = Tokenize(name)
        IsNegative = False
        negative_token = []
        token_filter = []
        
        for token in tokens:
            if token in token_filter:
                continue
            
            req = {
                "docs":[
                    {
                        "text_field": token
                        }
                    ],
            
            "inference_config": {
                "text_classification": {
                    "num_top_classes": 2
                    }
                }
            }

            resp = es.transport.perform_request('POST', "/_ml/trained_models/matthewburke__korean_sentiment/deployment/_infer" ,body=json.dumps(req), headers= header)
            
            if resp.body["top_classes"][0]["class_name"] == "LABEL_0" and resp.body["top_classes"][0]["class_score"] > 0.8:
                IsNegative = True
                negative_token += [{"name": token,
                                  "positive": resp.body["top_classes"][1]["class_score"], 
                                  "negative": resp.body["top_classes"][0]["class_score"]}]
        nodup = []
        for value in negative_token:
            if value not in nodup:
                nodup.append(value)
        result = {"result": IsNegative, "NegativeTokens": nodup}
        
        return result
    except Exception as e:
        st.write('error for checking')


def app(es: Elasticsearch):
    st.markdown(
    """
    <style>
    /* 제목 가운데 정렬 */
    .title-wrapper {
        display: flex;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True
    )
    #css수정
    st.markdown("<h1 style='text-align: center; color: blue; font-size: 60px'>TM Partner</h1>", unsafe_allow_html=True)
    first,mid,end=st.columns([10,11,10])
    with mid:
        st.markdown("<h2 style='text-align: center; color: black; font-size: 18px'>상표 등록을 위한 판단 보조 서비스</h2>", unsafe_allow_html=True)
    with end:
         st.image("titleimage.jpeg", width= 50)
    
    with st.form("form"):
        name = st.text_input('상표 이름', value=None)
        item = st.text_input('출원 물품', value=None)

        model = load_model()
        submitted = st.form_submit_button('입력')

        if submitted and name and item:
            with st.spinner("잠시만 기다려 주세요."):
                name.strip()
                item.strip()
                col1, col2, col3 = st.columns([1, 1, 1]) 

                with col1:
                    st.markdown("<h3 style='font-size:80%;'>동일한 상표 검사 결과</h3>", unsafe_allow_html=True)
                    resultforSame = queryForFindSameNameV2(name, es)
                    
                    if resultforSame["result"]:
                        st.success(resultforSame["msg"])
                    else:
                        st.info("등록된 상표 중 동일한 상표는 없습니다.")
                
                with col2:
                    result_negative = queryForCheckElastic(name, es)
                    st.markdown("<h3 style='font-size:80%;'>반사회성, 비도덕성 검사 결과</h3>", unsafe_allow_html=True)
                    if result_negative["result"]:
                        msg = ""
                        for idx, ans in enumerate(result_negative["NegativeTokens"]):
                            msg += f"{idx+1}. {ans['name']} \n"
                        
                        st.warning(msg)
                        
                    else:
                        st.info("부정적인 의미를 가진 단어가 발견되지 않았습니다.")
                with col3:
                    st.markdown("<h3 style='font-size:80%;'>관련도 검사 결과</h3>", unsafe_allow_html=True)
                    if item:
                        similarity = calculate_similarity(model, name, item)
                        if similarity >= 0.5:
                            st.info('출원 물품과 상표 사이의 관련성이 높습니다. 검토가 필요합니다.')
                        elif similarity < 0.5 and similarity >= 0.3:
                            st.info('출원 물품과 상표 사이의 관련성이 있어 보입니다. 검토를 권합니다.')
                        elif similarity < 0.3 and similarity >= 0.2:
                            st.info('출원 물품과 상표 사이의 관련성이 있을 수도 있습니다. 만약을 위해 검토를 해보는 것이 좋습니다')
                        else:
                            st.info('출원 물품과 상표 사이의 관련성이 적어보입니다.')
                    else:
                        st.info("출원 물품을 입력하지 않으셨습니다.")

                with st.container():
                    if result_negative["result"]:
                        for ans in result_negative["NegativeTokens"]:
                                    df = pd.DataFrame({
                                        "name": ['positive', 'negative'],
                                        "probability": [ans['positive'], ans['negative']]
                                        })
                                    fig = px.pie(df, values='probability', names='name', title= f"Pie Chart of \'{ans['name']}\'") 
                                    st.plotly_chart(fig, use_container_width=True)   
                    st.markdown("<h3 style='font-size:80%;'>발음이 유사한 상표 검사 결과</h3>", unsafe_allow_html=True)
                    result2 = queryForFindSimilarPronun(name, es)
                    
                    if result2["result"]:
                        # 이미지 출력을 위한 컬럼을 동적으로 생성하기 위해 임시 변수 선언
                        cols = None
                        for idx, (title, score, date, image_url) in enumerate(result2["data"], start=1):
                            # 한 줄에 이미지 두 개씩 출력하기 위해, idx가 홀수일 때 새로운 컬럼 생성
                            if idx % 2 == 1:
                                cols = st.columns(2)  # 두 개의 컬럼 생성
                            # idx가 짝수일 때는 cols[1]에, 홀수일 때는 cols[0]에 이미지를 출력
                            col = cols[(idx + 1) % 2]
                            with col:
                                try:
                                    # 먼저 date를 정수로 변환 시도
                                    date_int = int(float(date))  # float로 먼저 변환 후 int로 변환하여 소수점 제거
                                    date_str = str(date_int)  # 출력을 위해 문자열로 다시 변환
                                except ValueError:
                                    # 변환 실패(즉, date가 숫자가 아닌 경우) 시 date를 문자열로 처리
                                    date_str = date
                                st.write(f"{idx}. {title}  - 출원일: {int(date)}")
                                download_and_show_image(image_url)
                    else:
                        st.info("등록된 상표 중 발음이 유사한 상표는 없습니다.")
                        
                with st.container():  # 이미지 출력을 위한 컨테이너
                    st.markdown("<h3 style='font-size:80%;'>이외 검토가 필요한 상표들</h3>", unsafe_allow_html=True)
                    result3 = queryForFindSimilarName(name, es)
                    if result3["result"]:
                        # 이미지 출력을 위한 컬럼을 동적으로 생성하기 위해 임시 변수 선언
                        cols = None
                        for idx, (title, date, image_url) in enumerate(result3["data"], start=1):
                            # 한 줄에 이미지 두 개씩 출력하기 위해, idx가 홀수일 때 새로운 컬럼 생성
                            if idx % 2 == 1:
                                cols = st.columns(2)  # 두 개의 컬럼 생성
                            # idx가 짝수일 때는 cols[1]에, 홀수일 때는 cols[0]에 이미지를 출력
                            col = cols[(idx + 1) % 2]
                            with col:
                                try:
                                    # 먼저 date를 정수로 변환 시도
                                    date_int = int(float(date))  # float로 먼저 변환 후 int로 변환하여 소수점 제거
                                    date_str = str(date_int)  # 출력을 위해 문자열로 다시 변환
                                except ValueError:
                                    # 변환 실패(즉, date가 숫자가 아닌 경우) 시 date를 문자열로 처리
                                    date_str = date
                                st.write(f"{idx}. {title}  - 출원일: {int(date)}")
                                download_and_show_image(image_url)
                    else:
                        st.info("등록된 상표 중 전체적인 형태가 유사한 상표는 없습니다.")


    #css수정
    col1, col2, col3 = st.columns(3)  
    with col1:
        st.markdown("<h3 style='text-align: center; color: white; font-size: 15px; background-color: #4f94d4;'>1단계</h3>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: black; font-size: 15px; background-color: #f0f6fc;'>동일상표여부 검사</h3>", unsafe_allow_html=True)  #동일상표여부 검사
    with col2:
        st.markdown("<h3 style='text-align: center; color: white; font-size: 15px; background-color: #4f94d4;'>2단계</h3>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: black; font-size: 15px; background-color: #f0f6fc;'>부정적단어 검사</h3>", unsafe_allow_html=True)  #부정적단어 검사
    with col3:
        st.markdown("<h3 style='text-align: center; color: white; font-size: 15px;background-color: #4f94d4;'>3단계</h3>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: black; font-size: 15px;background-color: #f0f6fc;'>기존상표 유사도검사</h3>", unsafe_allow_html=True)  #기존상표 유사도검사<
              
def main():
    es = connectToElastic()
    app(es)

if __name__ == '__main__':
    main()
