# TrademarketProject

상표권이 등록되기 위해서 많은 조건을 충족해야할 필요가 있다. 하지만 저희는 그 중에서 중요도가 높은 조건 4가지를 선별하여 상표등록 가능성 여부를 판단해보았다. 

### 1. 상표에 등록되기 위해서 동일한 이름의 상표가 존재해서는 안된다.   
  N-gram tokenizer를 활용해 elasticsearch에 데이터 저장후 동일한 이름을 가진 상표명이 존재하는지 확인하였다.  


  
### 2. 상표에 등록되기 위해서 발음이 비슷한 상표가 존재해서는 안된다.   
  일단 elasticsearch에 저장된 모든 상표명에 대해 IPA발음 기호로 변환한 데이터를 저장한다.  
  Fuzzy query를 활용하여 그나마 발음이 유사한 것으로 판단되어지는 상표명을 검색한 이후 2차적으로 서버에서 발음이 유사성 여부를 평가해주는 프로그램을 통해 발음 유사도를 판단하였다.  


  
### 3. 공식적으로 사용하기에 부적절한 단어가 상표명에 포함되서는 안된다.  
   Huggingface에 배포된 단어의 positiveness와 negativeness의 정도를 측정해주는 AI를 활용해서 해당 단어가 비도덕적인지를 간접적으로 판단해보았다.  
   해당 AI는 elasticsearch cluster에 배포하여 이용하였다. 



### 4. 상표를 출원하려는 물품과 관련성이 없어야 한다.  
   예를 들어서 과일가게 이름을 Apple이라고 등록을 하면 안된다. 하지만 IT기업 이름을 Apple이라고 등록하는 것은 가능하다.
   Fasttext AI를 활용하여 상표명과 출원 물품간의 관련성 여부를 판단하였다. 

### 판별 예시
![Image](https://github.com/user-attachments/assets/75664ac4-1bf8-4e0d-840b-4377ea0b66be)
![Image](https://github.com/user-attachments/assets/0924dad4-2c4c-46a3-b1ad-23d636c2583a)
