class ToIPAService:
    def __init__(self):
        self.BASE_CODE = 0xAC00
        self.CHOSUNG = 588
        self.JUNGSUNG = 28

        self.CHOSUNG_LIST = [
            'ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ',
            'ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'
        ]

        self.JUNGSUNG_LIST = [
            'ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ',
            'ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ'
        ]

        self.JONGSUNG_LIST = [
            '', 'ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ',
            'ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ',
            'ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'
        ]
        
        self.FINAL_NEUTRALIZATION = {
            'ㄱ':'ㄱ', 'ㄲ':'ㄱ', 'ㅋ':'ㄱ',
            'ㄷ':'ㄷ', 'ㅌ':'ㄷ', 'ㅅ':'ㄷ', 'ㅆ':'ㄷ', 'ㅈ':'ㄷ', 'ㅊ':'ㄷ', 'ㅎ':'ㄷ',
            'ㅂ':'ㅂ', 'ㅍ':'ㅂ'
        }
        
        self.IPA_CONSONANT = {
            'ㄱ':'k', 'ㄲ':'k͈', 'ㅋ':'kʰ',
            'ㄷ':'t', 'ㄸ':'t͈', 'ㅌ':'tʰ',
            'ㅂ':'p', 'ㅃ':'p͈', 'ㅍ':'pʰ',
            'ㅅ':'s', 'ㅆ':'s͈',
            'ㅈ':'t͡ɕ', 'ㅉ':'t͡ɕ͈', 'ㅊ':'t͡ɕʰ',
            'ㄴ':'n', 'ㅁ':'m',
            'ㅇ':'ŋ', 'ㄹ':'ɾ', '':''
        }

        self.IPA_VOWEL = {
            'ㅏ':'a','ㅓ':'ʌ','ㅗ':'o','ㅜ':'u','ㅡ':'ɯ','ㅣ':'i',
            'ㅐ':'ɛ','ㅔ':'e'
        }

        self.IPA_FINAL = {
            'ㄱ':'k̚','ㄷ':'t̚','ㅂ':'p̚',
            'ㄴ':'n','ㅁ':'m','ㅇ':'ŋ','ㄹ':'l','':''
        }

    def neutralize_final(self, jong):
        return self.FINAL_NEUTRALIZATION.get(jong, jong)
    
    def apply_phonological_rules(self, syllables):
        result = []

        for i, (cho, jung, jong) in enumerate(syllables):
            # 종성 중화
            jong = self.neutralize_final(jong)

            # 연음
            if jong and i + 1 < len(syllables):
                next_cho, next_jung, next_jong = syllables[i + 1]
                if next_cho == 'ㅇ':
                    result.append((cho, jung, ''))
                    syllables[i + 1] = (jong, next_jung, next_jong)
                    continue

            result.append((cho, jung, jong))

        # 비음화
        for i in range(len(result) - 1):
            cho, jung, jong = result[i]
            ncho, njung, njong = result[i + 1]

            if jong == 'ㄱ' and ncho in ['ㄴ','ㅁ']:
                result[i] = (cho, jung, 'ㅇ')
            elif jong == 'ㄷ' and ncho in ['ㄴ','ㅁ']:
                result[i] = (cho, jung, 'ㄴ')
            elif jong == 'ㅂ' and ncho in ['ㄴ','ㅁ']:
                result[i] = (cho, jung, 'ㅁ')

        # 경음화
        TENSE = {'ㄱ':'ㄲ','ㄷ':'ㄸ','ㅂ':'ㅃ','ㅅ':'ㅆ','ㅈ':'ㅉ'}
        for i in range(len(result) - 1):
            _, _, jong = result[i]
            cho, jung, jong2 = result[i + 1]
            if jong and cho in TENSE:
                result[i + 1] = (TENSE[cho], jung, jong2)

        return result
    
    def decompose_hangul(self, char):
        code = ord(char) - self.BASE_CODE
        if code < 0 or code > 11171:
            return None

        cho = self.CHOSUNG_LIST[code // self.CHOSUNG]
        jung = self.JUNGSUNG_LIST[(code % self.CHOSUNG) // self.JUNGSUNG]
        jong = self.JONGSUNG_LIST[code % self.JUNGSUNG]

        return [cho, jung, jong]

    def hangul_to_ipa(self, text):
        syllables = []
        for ch in text:
            d = self.decompose_hangul(ch)
            if d:
                syllables.append(tuple(d))

        syllables = self.apply_phonological_rules(syllables)

        ipa = []
        for cho, jung, jong in syllables:
            ipa.append(
                self.IPA_CONSONANT.get(cho, '') +
                self.IPA_VOWEL.get(jung, '') +
                self.IPA_FINAL.get(jong, '')
            )

        return "[" + ".".join(ipa) + "]"
