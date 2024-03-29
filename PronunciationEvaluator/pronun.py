# Developed by DevTae@2023

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

#path = "" # base_path
path = Path(__file__).resolve().parent

# 자음 기준
# - 조음 위치, 유성음 여부
# - 조음 방법, 조음 강도

# Position (Bilabial) 0 --- 1 (Glottal)
conso_pos = { "Bilabial": 0, "Alveolar": 0.25, "Alveo-Palatal": 0.5, "Velar": 0.75, "Glottal": 1 }
# HowToPronunce (Plosive) 1 --- 0 (Lateral)
# 파열음(ㅂ, ㅍ, ㅃ, ㄷ, ㅌ, ㄸ, ㄱ, ㅋ, ㄲ), 마찰음(ㅅ, ㅆ, ㅎ), 파찰음(ㅈ, ㅊ, ㅉ), 비음(ㅁ, ㄴ, ㅇ), 유음(ㄹ)
conso_how = { "Plosive": 1, "Fricative": 0.5, "Affricate": 0.75, "Nasal": 0.25, "Lateral": 0 }
# Strength (Lenis) 0 --- 1 (Fortis)
conso_str = { "Lenis": 0, "Aspirated": 0.5, "Fortis": 1 }
# Voice or not (Yes) 0.5 --- 0 (No)
# 유성음인지 아닌지 구분
conso_voi = { "Yes": 0.5, "No": 0 }

consonants = pd.read_csv(os.path.join(path, "csv", "consonants.csv"))
consonants["조음강도"] = consonants["조음강도"].replace("None", "Lenis") # None -> Lenis
consonants = consonants.fillna("Lenis")

# 모음 기준
# - 입술 모양
# - 조음 좌우 위치, 조음 상하 위치

# shape (Unrounded) 0 --- 0.5 (Rounded)
vowel_shp = { "Unrounded": -0.5, "Rounded+Unrounded": -0.17, "Unrounded+Rounded": 0.17, "Rounded": 0.5 }
# width position (Front) 0 --- 1 (Back)
vowel_wps = { "Front": 0, "NearFront": 0.1, "Back+Front": 0.33, "Mid": 0.5, "Front+Back": 0.67, "NearBack": 0.9, "Back": 1 }
# height position (Low) 0 --- 1 (High)
vowel_hps = { "Low": 0, "NearLow": 0.1, "Mid+Low": 0.2, "High+Low": 0.4, "Mid": 0.5, "High+Mid": 0.7, "NearHigh" : 0.9, "High": 1 }

vowels = pd.read_csv(os.path.join(path, "csv", "vowels.csv"))


# data 에서 각 IPA 문자에 대응되는 수치를 저장한다.
def mapping_ipa_with_value(data):
    values = []
    types = []
    origs = []
    idx = 0
    while idx < len(data):
        ch = data[idx]
        skip = True
        for ipa in list(consonants["IPA"]):
            if data[idx:idx+len(ipa)] == ipa:
                skip = False
                conso_pos_ = conso_pos[consonants.loc[consonants["IPA"] == ipa]["조음위치"].iloc[0]]
                conso_how_ = conso_how[consonants.loc[consonants["IPA"] == ipa]["조음방법"].iloc[0]]
                conso_str_ = conso_str[consonants.loc[consonants["IPA"] == ipa]["조음강도"].iloc[0]]
                conso_voi_ = conso_voi[consonants.loc[consonants["IPA"] == ipa]["유성음여부"].iloc[0]]
                value = [conso_pos_, conso_how_, conso_str_, conso_voi_]
                values.append(value)
                if ipa == "ŋ": # 받침이 있는 경우, 'C' 가 아닌 'c' 로 등록하여 이후 처리에 반영한다.
                    types.append("c") # Consonants (받침)
                else:
                    types.append("C") # Consonants
                origs.append(ipa)
                idx += len(ipa)
        for ipa in list(vowels["IPA"]):
            if data[idx:idx+len(ipa)] == ipa:
                skip = False
                vowel_shp_ = vowel_shp[vowels.loc[vowels["IPA"] == ipa]["입술모양"].iloc[0]]
                vowel_wps_ = vowel_wps[vowels.loc[vowels["IPA"] == ipa]["조음좌우위치"].iloc[0]]
                vowel_hps_ = vowel_hps[vowels.loc[vowels["IPA"] == ipa]["조음상하위치"].iloc[0]]
                value = [vowel_shp_, vowel_wps_, vowel_hps_]
                values.append(value)
                types.append("V") # Vowels
                origs.append(ipa)
                idx += len(ipa)
        if skip == True:
            idx += 1
    return values, types, origs


# 자음과 모음이 한 발음 단위로 나뉘도록 분할
def split_types(types):
    result = []
    
    while len(types) > 0:
        if types.startswith("CVCC") or types.startswith("CVc"):
            result.append(types[:3])
            types = types[3:]
        elif types.startswith("CVCV") or types.startswith("CVV") or types.startswith("VCC") or types.startswith("Vc"):
            result.append(types[:2])
            types = types[2:]
        elif types.startswith("VCV") or types.startswith("VV") or types.startswith("cV") or types.upper().startswith("CC"):
            result.append(types[:1])
            types = types[1:]
        else:
            result.append(types[:])
            types = ""
    
    return result


# C+V 단위 Vectorization 진행
# [0] conso_pos
# [1] conso_how
# [2] conso_str
# [3] conso_voi
# [4] vowel_shp
# [5] vowel_wps
# [6] vowel_hps
# [7] support_conso_pos
# [8] support_how
# [9] support_str
# [10] support_voi
def vectorize_ipa(values, types, origs):
    vector_values = []
    vector_types = []
    vector_origs = []
    prev_type = None
    
    # C+V 단위 Vectorization
    types_after = split_types(''.join(types))
    
    idx = 0
    for types_ in types_after:
        vector_value = []
        vector_orig = []

        if types_ == "CVC" or types_ == "CVc":
            vector_value += values[idx]
            vector_value += values[idx+1]
            vector_value += values[idx+2]
            vector_orig.append(origs[idx])
            vector_orig.append(origs[idx+1])
            vector_orig.append(origs[idx+2])
        elif types_ == "CV":
            vector_value += values[idx]
            vector_value += values[idx+1]
            vector_value += [0, 0, 0, 0]
            vector_orig.append(origs[idx])
            vector_orig.append(origs[idx+1])
        elif types_ == "VC" or types_ == "Vc":
            vector_value += [0, 0, 0, 0]
            vector_value += values[idx]
            vector_value += values[idx+1]
            vector_orig.append(origs[idx])
            vector_orig.append(origs[idx+1])
        elif types_ == "V":
            vector_value += [0, 0, 0, 0]
            vector_value += values[idx]
            vector_value += [0, 0, 0, 0]
            vector_orig.append(origs[idx])
        elif types_ == "C":
            vector_value += values[idx]
            vector_value += [0, 0, 0]
            vector_value += [0, 0, 0, 0]
            vector_orig.append(origs[idx])
        elif types_ == "c":
            vector_value += [0, 0, 0, 0]
            vector_value += [0, 0, 0]
            vector_value += values[idx]
            vector_orig.append(origs[idx])
        else:
            print(types_after)
            print(types_)
            raise Exception("types_ 에 대하여 예기치 못한 입력값이 들어왔습니다.")
        
        vector_type = types_
        vector_values.append(vector_value)
        vector_types.append(vector_type)
        vector_origs.append(vector_orig)
        idx += len(types_)

    return vector_values, vector_types, vector_origs


# 두 pronunciation 사이에서의 score 를 구하는 함수 (1차원) (default)
def get_score_1d(values_ans, values_usr):
    assert isinstance(values_ans, list), "1차원 리스트에 대한 입력값만 지원합니다"
    assert not isinstance(values_ans[0], list), "1차원 리스트에 대한 입력값만 지원합니다"
    assert isinstance(values_usr, list), "1차원 리스트에 대한 입력값만 지원합니다"
    assert not isinstance(values_usr[0], list), "1차원 리스트에 대한 입력값만 지원합니다"
    
    # value_1 과 value_2 의 원소 배열 크기가 다른 경우 (자음 / 모음 타입 미일치), max distance (=1) 반환함.
    if len(values_ans) != len(values_usr):
        return 0 # min score 반환

    # 기본 점수 (여기서 점수를 곱하기로 차감해가는 방식으로 진행)
    score = 1.0

    # i. 자음의 경우
    # [ conso_pos_ (조음위치), conso_how_ (조음방법), conso_str_ (조음세기), conso_voi_ (유성음여부) ]
    if len(values_ans) == 4:
        # 조음위치 다르면 0 반환
        if values_ans[0] != values_usr[0]:
            return 0
        # 조음방법 다르면 0 반환
        elif values_ans[1] != values_usr[1]:
            return 0
        # 조음세기 및 유성음 미일치 시에 따른 점수 차감
        else:
            score *= 1 - abs(values_ans[2] - values_usr[2])
            score *= 1 - abs(values_ans[3] - values_usr[3])
            
    # ii. 모음의 경우
    # [ vowel_shp_ (입술 모양), vowel_wps_ (입술 좌우), vowel (입술 상하) ]
    elif len(values_ans) == 3:
        score *= 1 - abs(values_ans[0] - values_usr[0])
        score *= 1 - abs(values_ans[1] - values_usr[1])
        score *= 1 - abs(values_ans[2] - values_usr[2])
    else:
        return 0 # handling exception
        
    return score


# s1 : string of answer_ipa, s2 : string of user_ipa
def get_score(s1, s2, pivot=None, debug=False):
    if len(s1) < len(s2):
        return get_score(s2, s1, s1, debug)

    if len(s2) == 0:
        result_dict = dict()
        result_dict["answer_ipa"] = s1
        result_dict["user_ipa"] = s2
        result_dict["score"] = 0
        result_dict["summary"] = []
        return result_dict

    """
    values_ans, types_ans, origs_ans = mapping_ipa_with_value(s1)
    values_ans, types_ans, origs_ans = vectorize_ipa(values_ans, types_ans, origs_ans)
    values_usr, types_usr, origs_usr = mapping_ipa_with_value(s2)
    values_usr, types_usr, origs_usr = vectorize_ipa(values_usr, types_usr, origs_usr)
    """

    # 초성, 중성, 종성 부분은 STT 모델 결과가 문법 교정이 되어 있지 않기 때문에 나온 값 그대로 Levenshtein Distance 계산 진행
    values_ans, _, _ = mapping_ipa_with_value(s1)
    values_usr, _, _ = mapping_ipa_with_value(s2)

    previous_row = range(len(values_usr) + 1) # values_usr is shorter than values_ans (0 ~ len(values_usr))
    
    for i, c1 in enumerate(values_ans): # values_ans is longer than values_usr
        current_row = [i + 1]
        for j, c2 in enumerate(values_usr):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (1 - get_score_1d(c1, c2))
            current_row.append(min(insertions, deletions, substitutions))

        if debug:
            print(current_row[1:])

        previous_row = current_row

    per = previous_row[-1] / (len(values_ans) if pivot == None else len(values_usr))
    score = round(max(1 - per, 0), 2)

    # score 최댓값이 나오게 하는 path 파악
    result_dict = dict()
    if pivot == None:
        result_dict["answer_ipa"] = s1
        result_dict["user_ipa"] = s2
    else:
        result_dict["answer_ipa"] = s2
        result_dict["user_ipa"] = s1
    result_dict["score"] = score
    result_dict["summary"] = []

    pass # 피드백 부분 코드 필요함

    return result_dict    


"""
# values_1 과 values_2 에 대한 서로 대응하는 distance 를 계산한다.
# types_1 : answer, types_2 : user_input
def get_scores(values_ans, types_ans, values_usr, types_usr):
    scores = np.zeros((len(types_ans), len(types_usr)), dtype=float)
    
    for i in range(len(types_ans)):
        for j in range(len(types_usr)):
            scores[i][j] = get_score_1d(values_ans[i], values_usr[j])
            
    return scores

# 두 values 사이에서 score 채점 진행 (동적계획법 활용)
def get_score(answer_ipa, user_ipa, option="default"):
    values_ans, types_ans, origs_ans = mapping_ipa_with_value(answer_ipa)
    values_ans, types_ans, origs_ans = vectorize_ipa(values_ans, types_ans, origs_ans)
    values_usr, types_usr, origs_usr = mapping_ipa_with_value(user_ipa)
    values_usr, types_usr, origs_usr = vectorize_ipa(values_usr, types_usr, origs_usr)
    
    scores = get_scores(values_ans, types_ans, values_usr, types_usr)
    avg_of_scores = np.zeros((len(types_ans) + 1, len(types_usr) + 1), dtype=float)
    cnt_of_directions = np.zeros((len(types_ans) + 1, len(types_usr) + 1), dtype=float) # direction counting
    directions = np.empty((len(types_ans) + 1, len(types_usr) + 1), dtype='U') # best path 의 방향 저장

    # 기본 설정
    avg_of_scores[:,0] = 0
    avg_of_scores[0,:] = 0
    for i in range(1, len(types_ans) + 1):
        cnt_of_directions[i][0] = i - 1
    
    # 평균이 최대가 되는 경우를 찾게 됨
    for i in range(1, len(types_ans) + 1):
        for j in range(1, len(types_usr) + 1):
            # right 두 개로 하나를 채우는 것이기 때문에 cnt 2 증가
            expected_right = (avg_of_scores[i][j-1] * cnt_of_directions[i][j-1] + scores[i-1][j-1]) / (cnt_of_directions[i][j-1] + 2)
            if avg_of_scores[i][j] < expected_right:
                avg_of_scores[i][j] = expected_right
                cnt_of_directions[i][j] = cnt_of_directions[i][j-1] + 2
                directions[i][j] = "r"
            
            # bottom 하나로 두 개를 떼우려는 것이기에 cnt 3 증가
            expected_bottom = (avg_of_scores[i-1][j] * cnt_of_directions[i-1][j] + scores[i-1][j-1]) / (cnt_of_directions[i-1][j] + 3)
            if avg_of_scores[i][j] < expected_bottom:
                avg_of_scores[i][j] = expected_bottom
                cnt_of_directions[i][j] = cnt_of_directions[i-1][j] + 3
                directions[i][j] = "b"
            
            # diagonal
            expected_diagonal = (avg_of_scores[i-1][j-1] * cnt_of_directions[i-1][j-1] + scores[i-1][j-1]) / (cnt_of_directions[i-1][j-1] + 1)
            if avg_of_scores[i][j] < expected_diagonal:
                avg_of_scores[i][j] = expected_diagonal
                directions[i][j] = "d"
                cnt_of_directions[i][j] = cnt_of_directions[i-1][j-1] + 1
     
    # score 계산 및 score 가 최대가 되는 i(=answer), j(=user) 계산
    i = len(types_ans)
    j = min(i, len(types_usr))
    max_score = 0
    for j_ in range(i, len(types_usr) + 1):
        score = avg_of_scores[i][j_]
        if score > max_score:
            max_score = score
            j = j_
    
    # score 최댓값
    score = avg_of_scores[i][j]
    
    if option == "score":
        return score
    elif option == "default":
        # score 최댓값이 나오게 하는 path 파악
        result_dict = dict()
        result_dict["answer_ipa"] = answer_ipa
        result_dict["user_ipa"] = user_ipa
        result_dict["score"] = score
        result_dict["summary"] = []
        
        answer_ipa_splited = []
        user_ipa_splited = []
        per_scores = []
        
        while True:
            direction = directions[i][j]
            
            if direction == '':
                break
            
            answer_ipa_splited.append(origs_ans[i-1])
            user_ipa_splited.append(origs_usr[j-1])
            per_scores.append(scores[i-1][j-1])
            
            if direction == 'r':
                j -= 1
            elif direction == 'b':
                i -= 1
            elif direction == 'd':
                i -= 1
                j -= 1

        # 전체 정답 중에서 중간부터 채점한 게 높을 땐, 이전 문제 채점도 추가.
        while i > 0:
            answer_ipa_splited.append(origs_ans[i-1])
            user_ipa_splited.append([])
            per_scores.append(0)
            i -= 1  
        
        for answer_ipa_char, user_ipa_char, per_score in zip(answer_ipa_splited, user_ipa_splited, per_scores):
            result_dict["summary"].append([answer_ipa_char, user_ipa_char, per_score])
            
        result_dict["summary"].reverse() 

        return result_dict
"""

# for test
#if __name__ == "__main__":
#    print(get_score("ɑnnjʌŋɑsɛjo", "ɑnnjjmassɛjjo"))
