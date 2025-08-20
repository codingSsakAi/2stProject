import logging
import re
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class KeywordMapper:
    """사용자 자연어를 보험 전문 용어로 변환하는 키워드 매핑 시스템"""

    def __init__(self):
        self.keyword_mappings = self._initialize_keyword_mappings()
        self.question_patterns = self._initialize_question_patterns()

    def _initialize_keyword_mappings(self) -> Dict[str, str]:
        """키워드 매핑 사전 초기화"""
        return {
            # 사람 관련 표현
            "사람": "거주자",
            "직장인": "근로소득이 있는 거주자",
            "월급쟁이": "근로소득이 있는 거주자",
            "회사원": "근로소득이 있는 거주자",
            "사업자": "사업소득이 있는 거주자",
            "자영업자": "사업소득이 있는 거주자",
            "운전자": "자동차운전자",
            "차주": "자동차소유자",
            "보험가입자": "계약자",
            "보험받는사람": "피보험자",
            "보험금받는사람": "수익자",
            
            # 소득 관련 표현
            "연봉": "총급여액",
            "월급": "근로소득",
            "급여": "근로소득",
            "임금": "근로소득",
            "수입": "소득",
            "벌이": "소득",
            "수익": "소득",
            
            # 세금 관련 표현
            "세금": "소득세",
            "납세": "소득세 납부",
            "세금내기": "소득세 납부",
            "세금계산": "소득세 계산",
            "세율": "소득세율",
            
            # 공제 관련 표현
            "공제받다": "공제를 적용받다",
            "공제받을수있다": "공제를 적용받을 수 있다",
            "공제혜택": "공제 혜택",
            "세금공제": "세액공제",
            "소득공제": "소득공제",
            
            # 계산 관련 표현
            "얼마나내야하나": "세액은 얼마인가",
            "얼마나내야해": "세액은 얼마인가",
            "계산해줘": "계산하면 얼마인가",
            "얼마나될까": "얼마나 될까",
            "비용": "보험료",
            "가격": "보험료",
            "요금": "보험료",
            
            # 자동차 관련 표현
            "차": "자동차",
            "자동차": "자동차",
            "승용차": "승용자동차",
            "트럭": "화물자동차",
            "버스": "승합자동차",
            "오토바이": "이륜자동차",
            "배": "선박",
            "비행기": "항공기",
            
            # 사고 관련 표현
            "사고": "보험사고",
            "교통사고": "교통사고",
            "충돌": "충돌사고",
            "추돌": "추돌사고",
            "도망": "히트앤런",
            "무면허": "무면허운전",
            "음주": "음주운전",
            "과속": "과속운전",
            
            # 보험 관련 표현
            "보험": "보험",
            "자동차보험": "자동차보험",
            "생명보험": "생명보험",
            "손해보험": "손해보험",
            "건강보험": "건강보험",
            "연금보험": "연금보험",
            "여행보험": "여행보험",
            "재산보험": "재산보험",
            
            # 계약 관련 표현
            "가입": "보험가입",
            "계약": "보험계약",
            "체결": "계약체결",
            "해지": "계약해지",
            "변경": "계약변경",
            "갱신": "계약갱신",
            "만료": "계약만료",
            "연장": "계약연장",
            
            # 보험금 관련 표현
            "보험금": "보험금",
            "배상": "배상금",
            "청구": "보험금청구",
            "지급": "보험금지급",
            "받다": "보험금을 받다",
            "받을수있다": "보험금을 받을 수 있다",
            "얼마받을수있다": "얼마나 보험금을 받을 수 있는가",
            
            # 면책 관련 표현
            "면책": "면책",
            "면제": "면제",
            "책임없다": "책임이 없다",
            "배상안한다": "배상하지 않는다",
            "보험금안준다": "보험금을 지급하지 않는다",
            
            # 절차 관련 표현
            "신고": "사고신고",
            "절차": "처리절차",
            "방법": "처리방법",
            "어떻게": "어떻게",
            "언제": "언제",
            "어디서": "어디서",
            "무엇을": "무엇을",
            
            # 시간 관련 표현
            "언제까지": "기한",
            "기간": "기간",
            "기한": "기한",
            "마감": "마감일",
            "기한내": "기한 내",
            "기한초과": "기한 초과",
            
            # 장소 관련 표현
            "어디": "어디",
            "장소": "장소",
            "지역": "지역",
            "사무실": "사무실",
            "지점": "지점",
            "본사": "본사",
            "지사": "지사",
        }

    def _initialize_question_patterns(self) -> List[Dict[str, Any]]:
        """질문 패턴 초기화"""
        return [
            {
                "pattern": r"(얼마나|몇|어느정도).*?(내야|납부|지불)",
                "replacement": "세액은 얼마인가",
                "category": "calculation"
            },
            {
                "pattern": r"(언제|몇시|어느때).*?(내야|납부|지불)",
                "replacement": "납부기한은 언제인가",
                "category": "deadline"
            },
            {
                "pattern": r"(어디서|어느곳|어느장소).*?(내야|납부|지불)",
                "replacement": "납부장소는 어디인가",
                "category": "location"
            },
            {
                "pattern": r"(어떻게|어떤방법으로).*?(내야|납부|지불)",
                "replacement": "납부방법은 어떻게인가",
                "category": "method"
            },
            {
                "pattern": r"(왜|어째서|무슨이유로).*?(내야|납부|지불)",
                "replacement": "납부이유는 무엇인가",
                "category": "reason"
            },
            {
                "pattern": r"(무엇을|어떤것을).*?(받을수|받을수있다)",
                "replacement": "어떤 혜택을 받을 수 있는가",
                "category": "benefit"
            },
            {
                "pattern": r"(언제|몇시|어느때).*?(받을수|받을수있다)",
                "replacement": "언제 혜택을 받을 수 있는가",
                "category": "timing"
            },
            {
                "pattern": r"(어떻게|어떤절차로).*?(받을수|받을수있다)",
                "replacement": "어떤 절차로 혜택을 받을 수 있는가",
                "category": "procedure"
            }
        ]

    def map_keywords(self, text: str) -> str:
        """텍스트의 키워드를 보험 전문 용어로 변환"""
        if not text:
            return text
        
        try:
            mapped_text = text
            
            # 키워드 매핑 적용
            for natural_keyword, professional_keyword in self.keyword_mappings.items():
                # 대소문자 구분 없이 매칭
                pattern = re.compile(re.escape(natural_keyword), re.IGNORECASE)
                mapped_text = pattern.sub(professional_keyword, mapped_text)
            
            # 질문 패턴 매핑 적용
            for pattern_info in self.question_patterns:
                pattern = re.compile(pattern_info["pattern"], re.IGNORECASE)
                if pattern.search(mapped_text):
                    mapped_text = pattern.sub(pattern_info["replacement"], mapped_text)
                    break
            
            logger.info(f"키워드 매핑 완료: {text[:50]}... -> {mapped_text[:50]}...")
            return mapped_text
            
        except Exception as e:
            logger.error(f"키워드 매핑 중 오류: {e}")
            return text

    def extract_keywords_from_text(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        if not text:
            return []
        
        try:
            extracted_keywords = []
            
            # 매핑된 키워드들 중에서 텍스트에 포함된 것들 찾기
            for natural_keyword, professional_keyword in self.keyword_mappings.items():
                if natural_keyword.lower() in text.lower():
                    extracted_keywords.append(professional_keyword)
                elif professional_keyword.lower() in text.lower():
                    extracted_keywords.append(professional_keyword)
            
            # 중복 제거
            extracted_keywords = list(set(extracted_keywords))
            
            logger.info(f"키워드 추출 완료: {extracted_keywords}")
            return extracted_keywords
            
        except Exception as e:
            logger.error(f"키워드 추출 중 오류: {e}")
            return []

    def get_related_keywords(self, keyword: str) -> List[str]:
        """관련 키워드 반환"""
        related_keywords = []
        
        try:
            # 동일한 매핑 그룹에서 관련 키워드 찾기
            for natural_keyword, professional_keyword in self.keyword_mappings.items():
                if professional_keyword == keyword:
                    # 같은 professional_keyword를 가진 다른 natural_keyword들 찾기
                    for other_natural, other_professional in self.keyword_mappings.items():
                        if other_professional == professional_keyword and other_natural != natural_keyword:
                            related_keywords.append(other_natural)
            
            logger.info(f"관련 키워드 조회: {keyword} -> {related_keywords}")
            return related_keywords
            
        except Exception as e:
            logger.error(f"관련 키워드 조회 중 오류: {e}")
            return []

    def get_keyword_statistics(self) -> Dict[str, Any]:
        """키워드 매핑 통계 정보"""
        stats = {
            'total_mappings': len(self.keyword_mappings),
            'professional_keywords': set(),
            'categories': {
                'people': 0,
                'income': 0,
                'tax': 0,
                'deduction': 0,
                'calculation': 0,
                'vehicle': 0,
                'accident': 0,
                'insurance': 0,
                'contract': 0,
                'payment': 0,
                'exemption': 0,
                'procedure': 0,
                'time': 0,
                'location': 0
            }
        }
        
        try:
            for natural_keyword, professional_keyword in self.keyword_mappings.items():
                stats['professional_keywords'].add(professional_keyword)
                
                # 카테고리 분류 (키워드 내용 기반)
                if any(word in natural_keyword for word in ['사람', '직장인', '회사원', '운전자', '가입자']):
                    stats['categories']['people'] += 1
                elif any(word in natural_keyword for word in ['연봉', '월급', '급여', '소득', '수입']):
                    stats['categories']['income'] += 1
                elif any(word in natural_keyword for word in ['세금', '납세', '세율']):
                    stats['categories']['tax'] += 1
                elif any(word in natural_keyword for word in ['공제', '혜택']):
                    stats['categories']['deduction'] += 1
                elif any(word in natural_keyword for word in ['계산', '얼마', '비용']):
                    stats['categories']['calculation'] += 1
                elif any(word in natural_keyword for word in ['차', '자동차', '승용차', '트럭']):
                    stats['categories']['vehicle'] += 1
                elif any(word in natural_keyword for word in ['사고', '교통', '충돌', '무면허']):
                    stats['categories']['accident'] += 1
                elif any(word in natural_keyword for word in ['보험']):
                    stats['categories']['insurance'] += 1
                elif any(word in natural_keyword for word in ['계약', '가입', '해지', '변경']):
                    stats['categories']['contract'] += 1
                elif any(word in natural_keyword for word in ['보험금', '배상', '지급', '받다']):
                    stats['categories']['payment'] += 1
                elif any(word in natural_keyword for word in ['면책', '면제', '책임없다']):
                    stats['categories']['exemption'] += 1
                elif any(word in natural_keyword for word in ['절차', '방법', '어떻게']):
                    stats['categories']['procedure'] += 1
                elif any(word in natural_keyword for word in ['언제', '기간', '기한']):
                    stats['categories']['time'] += 1
                elif any(word in natural_keyword for word in ['어디', '장소', '지역']):
                    stats['categories']['location'] += 1
            
            stats['professional_keywords'] = list(stats['professional_keywords'])
            stats['unique_professional_keywords'] = len(stats['professional_keywords'])
            
            return stats
            
        except Exception as e:
            logger.error(f"키워드 통계 생성 중 오류: {e}")
            return stats

    def add_custom_mapping(self, natural_keyword: str, professional_keyword: str) -> bool:
        """사용자 정의 키워드 매핑 추가"""
        try:
            self.keyword_mappings[natural_keyword] = professional_keyword
            logger.info(f"사용자 정의 매핑 추가: {natural_keyword} -> {professional_keyword}")
            return True
        except Exception as e:
            logger.error(f"사용자 정의 매핑 추가 중 오류: {e}")
            return False

    def remove_mapping(self, natural_keyword: str) -> bool:
        """키워드 매핑 제거"""
        try:
            if natural_keyword in self.keyword_mappings:
                del self.keyword_mappings[natural_keyword]
                logger.info(f"키워드 매핑 제거: {natural_keyword}")
                return True
            return False
        except Exception as e:
            logger.error(f"키워드 매핑 제거 중 오류: {e}")
            return False
