import re
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class KeywordExpansionService:
    """
    자동차보험 전문 용어 사전과 키워드 확장 기능
    """

    def __init__(self):
        # 자동차보험 전문 용어 사전
        self.insurance_synonyms = {
            # 연락처 관련
            "연락처": [
                "전화번호",
                "연락",
                "연락처",
                "고객센터",
                "상담전화",
                "문의전화",
                "고객지원",
                "상담",
                "문의",
            ],
            "전화번호": [
                "연락처",
                "전화",
                "고객센터",
                "상담전화",
                "문의전화",
                "고객지원",
                "상담",
                "문의",
            ],
            "고객센터": [
                "연락처",
                "전화번호",
                "상담전화",
                "문의전화",
                "고객지원",
                "상담",
                "문의",
            ],
            # 보험 해지 관련
            "보험해지": [
                "계약해지",
                "보험계약해지",
                "해지절차",
                "해지신청",
                "해지방법",
                "보험해지방법",
                "계약해지방법",
            ],
            "해지": ["계약해지", "보험해지", "해지신청", "해지절차", "해지방법"],
            "계약해지": ["보험해지", "해지", "해지신청", "해지절차", "해지방법"],
            # 보험금 청구 관련
            "보험금청구": [
                "보험금지급",
                "보험금신청",
                "보상청구",
                "보험금지급신청",
                "보험금청구절차",
            ],
            "보험금": ["보상금", "보험지급금", "보험보상금", "보험금액"],
            "보상": ["보험금", "보상금", "보험지급", "보험보상"],
            # 사고 관련
            "사고": ["교통사고", "자동차사고", "충돌사고", "교통상해", "교통사고발생"],
            "교통사고": ["자동차사고", "충돌사고", "교통상해", "사고"],
            "충돌": ["사고", "교통사고", "자동차사고", "충돌사고"],
            # 보험료 관련
            "보험료": ["보험료율", "보험료금액", "보험료납부", "보험료납입"],
            "보험료납부": ["보험료납입", "보험료지급", "보험료결제"],
            # 보험가입 관련
            "보험가입": ["보험계약", "보험계약체결", "보험가입신청", "보험계약체결"],
            "보험계약": ["보험가입", "보험계약체결", "보험계약서"],
            # 면책 관련
            "면책": ["면책사유", "면책조항", "보험면책", "면책규정"],
            "면책사유": ["면책", "면책조항", "보험면책", "면책규정"],
            # 무보험 관련
            "무보험": ["무보험자동차", "무보험차량", "무보험운전"],
            "무보험자동차": ["무보험", "무보험차량", "무보험운전"],
            # 특별약관 관련
            "특별약관": ["특약", "특별보장", "추가보장", "특별보험"],
            "특약": ["특별약관", "특별보장", "추가보장", "특별보험"],
            # 보험사 관련
            "보험사": ["보험회사", "보험업체", "보험기관"],
            "보험회사": ["보험사", "보험업체", "보험기관"],
            # 피보험자 관련
            "피보험자": ["보험가입자", "보험계약자", "보험대상자"],
            "보험가입자": ["피보험자", "보험계약자", "보험대상자"],
            # 피해자 관련
            "피해자": ["사고피해자", "교통사고피해자", "상해자"],
            "사고피해자": ["피해자", "교통사고피해자", "상해자"],
            # 가해자 관련
            "가해자": ["사고가해자", "교통사고가해자", "사고원인자"],
            "사고가해자": ["가해자", "교통사고가해자", "사고원인자"],
        }

        # 한국어 형태소 분석을 위한 기본 패턴
        self.korean_patterns = {
            "하다": ["하", "한", "하는", "했", "할"],
            "되다": ["되", "된", "되는", "됐", "될"],
            "받다": ["받", "받은", "받는", "받았", "받을"],
            "지급하다": ["지급", "지급한", "지급하는", "지급했", "지급할"],
            "청구하다": ["청구", "청구한", "청구하는", "청구했", "청구할"],
            "신청하다": ["신청", "신청한", "신청하는", "신청했", "신청할"],
        }

    def expand_keywords(self, query: str) -> List[str]:
        """
        사용자 질문에서 키워드를 추출하고 확장된 키워드 목록을 반환
        """
        expanded_keywords = [query]  # 원본 질문 포함

        # 1. 동의어 확장
        for keyword, synonyms in self.insurance_synonyms.items():
            if keyword in query:
                expanded_keywords.extend(synonyms)

        # 2. 형태소 변형 확장
        for base_form, variations in self.korean_patterns.items():
            if base_form in query:
                for variation in variations:
                    expanded_query = query.replace(base_form, variation)
                    if expanded_query not in expanded_keywords:
                        expanded_keywords.append(expanded_query)

        # 3. 키워드 조합 확장
        combined_keywords = self._generate_combinations(query)
        expanded_keywords.extend(combined_keywords)

        # 중복 제거 및 정렬
        unique_keywords = list(set(expanded_keywords))
        unique_keywords.sort(key=len, reverse=True)  # 긴 키워드부터 정렬

        logger.info(f"키워드 확장 결과: {query} -> {unique_keywords[:5]}...")
        return unique_keywords

    def _generate_combinations(self, query: str) -> List[str]:
        """
        키워드 조합을 생성 (예: "보험해지" -> "보험 해지", "보험+해지")
        """
        combinations = []

        # 공백으로 분리 가능한 조합
        if len(query) > 2:
            for i in range(1, len(query)):
                part1 = query[:i]
                part2 = query[i:]
                if part1 and part2:
                    combinations.append(f"{part1} {part2}")
                    combinations.append(f"{part1}+{part2}")

        # 특정 패턴 조합
        if "보험" in query and "해지" in query:
            combinations.extend(["보험 해지", "보험+해지", "보험계약해지"])
        if "보험" in query and "청구" in query:
            combinations.extend(["보험 청구", "보험+청구", "보험금청구"])
        if "사고" in query and "처리" in query:
            combinations.extend(["사고 처리", "사고+처리", "교통사고처리"])

        return combinations

    def get_relevant_keywords(self, query: str, top_n: int = 8) -> List[str]:
        """
        가장 관련성 높은 키워드만 반환 (개선된 버전)
        """
        expanded = self.expand_keywords(query)
        # 원본 질문과 가장 유사한 키워드들을 우선 선택
        relevant = [query]

        # 1. 동의어 키워드 우선 추가
        for keyword in expanded:
            if keyword != query and len(relevant) < top_n:
                # 동의어 사전에 있는 키워드 우선
                if any(
                    keyword in synonyms for synonyms in self.insurance_synonyms.values()
                ):
                    relevant.append(keyword)

        # 2. 질문에서 추출한 핵심 키워드 추가
        query_words = query.split()
        for word in query_words:
            if len(word) >= 2 and word not in relevant and len(relevant) < top_n:
                relevant.append(word)

        # 3. 나머지 확장 키워드 추가
        for keyword in expanded:
            if keyword not in relevant and len(relevant) < top_n:
                if len(keyword) >= 2:
                    relevant.append(keyword)

        return relevant[:top_n]

    def normalize_query(self, query: str) -> str:
        """
        질문을 정규화 (공백 정리, 특수문자 처리)
        """
        # 공백 정리
        normalized = re.sub(r"\s+", " ", query.strip())
        # 특수문자 처리
        normalized = re.sub(r"[^\w\s가-힣]", "", normalized)
        return normalized
