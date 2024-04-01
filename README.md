# TrademarketProject
check whether trademark can be registered

![상표](https://github.com/MVPatM/TrademarketProject/assets/76089856/2ff5a5d4-e4ab-4dd0-a49d-7c8e0c163662)

상표권을 등록을 하려면 다음 조건들이 필요하다.
1. 동일한 이름을 가진 상표가 존재해서는 안된다.
  n-gram tokenizer를 활용을 해서 elasticsearch에 데이터를 저장을 하고
  동일한 이름을 가진 상표명이 존재하는 지를 검색을 하였다.

3. 발음이 비슷한 상표가 존재해서는 안된다.
  일단 elasticsearch에 모든 상표명에 대한 IPA발음 기호를 저장을 한다.
  먼저 fuzzy query를 활용을 해서 그나마 발음이 유사한 것으로 판단이 되어지는 상표명을 추출을 한다. 
  그리고 2차적으로 IPA발음 기호를 활용을 해서 발음이 유사한지 평가해주는 프로그램을 활용을 하였다.
  상표에 따라서 발음 기호 유사도가 다르게 설정을 해놓았다.
  유명한 상표는 유사도 임계치를 낮게 설정을 해서 조금이라도 비슷하면 유사하다고 판단하게 하였다.

5. 비도덕적인 말이 상표안에 포함이 되서는 안된다.
   huggingface에서 positive와 negative를 평가를 해주는 AI를 활용을 해서 판단을 진행하였다.
   해당 AI는 elasticsearch에 deploy를 시켰다.

6. 상표를 출원하려는 물품과 관련이 없는 이름이여야한다.
   예를 들어서 과일가게 이름을 Apple이라고 등록을 하면 안된다.
   하지만 IT기업 이름을 Apple이라고 등록을 하는 것은 가능하다.

   fasttext AI를 활용을 해서 구현을 하였다.
   해당 AI는 ec2와 ebs를 활용을 해서 deploy시켜놓았다. 
