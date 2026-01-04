import fasttext
import numpy as np
from typing import Dict

class FastTextService:
    def __init__(self):
        self.model = fasttext.load_model('kor.bin')
        
    def _calculate_similarity(self, trademark_name: str, product_name: str):
        refined_name = trademark_name.replace(product_name, "").strip()
        vector1 = self.model.get_sentence_vector(refined_name)
        vector2 = self.model.get_sentence_vector(product_name)
        similarity = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
        
        if np.isnan(similarity):
            similarity = 0
            
        return similarity
    
    def getSimilarity(self, name: str, item: str) -> Dict[str, str]:
        similarity = self._calculate_similarity(self.model, name, item)
        if similarity >= 0.5:
            return {"result": '출원 물품과 상표 사이의 관련성이 높습니다. 검토가 필요합니다.'}
        elif similarity < 0.5 and similarity >= 0.3:
            return {"result": '출원 물품과 상표 사이의 관련성이 있어 보입니다. 검토를 권합니다.'}
        elif similarity < 0.3 and similarity >= 0.2:
            return {"result": '출원 물품과 상표 사이의 관련성이 있을 수도 있습니다. 만약을 위해 검토를 해보는 것이 좋습니다'}
        else:
            return {"result": '출원 물품과 상표 사이의 관련성이 적어보입니다.'}
