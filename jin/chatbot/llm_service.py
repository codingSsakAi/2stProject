import logging
import time
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Ollama 클라이언트 임포트 (선택적)
try:
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama 클라이언트를 사용할 수 없습니다. langchain-ollama 패키지를 설치하세요.")


class OllamaLLMService:
    """Ollama 로컬 LLM 서비스"""

    def __init__(self, model_name: str = "exaone3.5:2.4b"):
        self.model_name = model_name
        self.llm = None
        self._initialize_ollama()

    def _initialize_ollama(self):
        """Ollama 초기화"""
        if not OLLAMA_AVAILABLE:
            logger.error("❌ Ollama 클라이언트를 사용할 수 없습니다.")
            return

        try:
            self.llm = ChatOllama(
                model=self.model_name,
                temperature=0.1,  # 일관된 답변을 위해 낮은 온도
                num_predict=50,   # 최대 토큰 수 제한
                base_url="http://localhost:11434"  # 로컬 Ollama 서버
            )
            logger.info(f"✅ Ollama LLM 초기화 완료 - 모델: {self.model_name}")
        except Exception as e:
            logger.error(f"❌ Ollama 초기화 실패: {e}")
            self.llm = None

    def is_available(self) -> bool:
        """Ollama 사용 가능 여부 확인"""
        return OLLAMA_AVAILABLE and self.llm is not None

    def extract_title(self, content: str) -> str:
        """제목 추출"""
        if not self.is_available():
            logger.warning("Ollama를 사용할 수 없어 기본 제목을 반환합니다.")
            return self._get_default_title(content)

        try:
            prompt = self._create_title_prompt(content)
            response = self.llm.invoke([HumanMessage(content=prompt)])
            title = self._clean_title(response.content)
            logger.info(f"제목 추출 완료: {title[:50]}...")
            return title
        except Exception as e:
            logger.error(f"제목 추출 중 오류: {e}")
            return self._get_default_title(content)

    def classify_category(self, content: str) -> str:
        """카테고리 분류"""
        if not self.is_available():
            logger.warning("Ollama를 사용할 수 없어 기본 카테고리를 반환합니다.")
            return self._get_default_category(content)

        try:
            prompt = self._create_category_prompt(content)
            response = self.llm.invoke([HumanMessage(content=prompt)])
            category = self._parse_category(response.content)
            logger.info(f"카테고리 분류 완료: {category}")
            return category
        except Exception as e:
            logger.error(f"카테고리 분류 중 오류: {e}")
            return self._get_default_category(content)

    def extract_keywords(self, content: str, max_keywords: int = 5) -> List[str]:
        """키워드 추출"""
        if not self.is_available():
            logger.warning("Ollama를 사용할 수 없어 기본 키워드를 반환합니다.")
            return self._get_default_keywords(content, max_keywords)

        try:
            prompt = self._create_keyword_prompt(content, max_keywords)
            response = self.llm.invoke([HumanMessage(content=prompt)])
            keywords = self._parse_keywords(response.content)
            logger.info(f"키워드 추출 완료: {keywords}")
            return keywords
        except Exception as e:
            logger.error(f"키워드 추출 중 오류: {e}")
            return self._get_default_keywords(content, max_keywords)

    def generate_summary(self, content: str, max_length: int = 100) -> str:
        """요약 생성"""
        if not self.is_available():
            logger.warning("Ollama를 사용할 수 없어 기본 요약을 반환합니다.")
            return self._get_default_summary(content, max_length)

        try:
            prompt = self._create_summary_prompt(content, max_length)
            response = self.llm.invoke([HumanMessage(content=prompt)])
            summary = self._clean_summary(response.content)
            logger.info(f"요약 생성 완료: {len(summary)} 문자")
            return summary
        except Exception as e:
            logger.error(f"요약 생성 중 오류: {e}")
            return self._get_default_summary(content, max_length)

    def _create_title_prompt(self, content: str) -> str:
        """제목 추출 프롬프트 생성"""
        return f"""다음 보험 약관 조문의 핵심 제목을 30토큰 이내로 간단히 완벽하게 말이 되도록 추출해 주세요. 
중간에 말이 끊기면 안 되고, 보험 업계에서 통용되는 용어를 사용해 주세요.

조문 내용: {content[:1000]}

제목 형식: "주제 : 세부내용"
예시: "자동차보험 면책사유 : 고의사고, 무면허운전, 음주운전"

답변:"""

    def _create_category_prompt(self, content: str) -> str:
        """카테고리 분류 프롬프트 생성"""
        categories = [
            "가입/계약관리", "보험료관리", "보험금지급", "면책/배상", 
            "사고처리", "특약/부가보장", "기타"
        ]
        
        return f"""다음 보험 약관 내용을 분석하여 가장 적합한 카테고리를 선택해 주세요.

카테고리 목록:
{', '.join(categories)}

조문 내용: {content[:1000]}

답변 형식: 카테고리명만 출력
답변:"""

    def _create_keyword_prompt(self, content: str, max_keywords: int) -> str:
        """키워드 추출 프롬프트 생성"""
        return f"""다음 보험 약관 내용에서 핵심 키워드 {max_keywords}개를 추출해 주세요.
보험 업계에서 자주 사용되는 전문 용어를 우선적으로 선택해 주세요.

조문 내용: {content[:1000]}

답변 형식: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5
답변:"""

    def _create_summary_prompt(self, content: str, max_length: int) -> str:
        """요약 생성 프롬프트 생성"""
        return f"""다음 보험 약관 내용을 {max_length}자 이내로 간단히 요약해 주세요.
핵심 내용만 포함하고, 일반인이 이해하기 쉽게 작성해 주세요.

조문 내용: {content[:1000]}

답변:"""

    def _clean_title(self, title: str) -> str:
        """제목 정제"""
        if not title:
            return ""
        
        # 불필요한 문자 제거
        title = title.strip()
        title = title.replace('"', '').replace("'", '')
        
        # 길이 제한
        if len(title) > 500:
            title = title[:500] + "..."
        
        return title

    def _parse_category(self, category: str) -> str:
        """카테고리 파싱"""
        if not category:
            return "기타"
        
        category = category.strip()
        valid_categories = [
            "가입/계약관리", "보험료관리", "보험금지급", "면책/배상", 
            "사고처리", "특약/부가보장", "기타"
        ]
        
        for valid_cat in valid_categories:
            if valid_cat in category:
                return valid_cat
        
        return "기타"

    def _parse_keywords(self, keywords: str) -> List[str]:
        """키워드 파싱"""
        if not keywords:
            return []
        
        # 쉼표로 분리
        keyword_list = [kw.strip() for kw in keywords.split(',')]
        # 빈 문자열 제거
        keyword_list = [kw for kw in keyword_list if kw]
        
        return keyword_list

    def _clean_summary(self, summary: str) -> str:
        """요약 정제"""
        if not summary:
            return ""
        
        summary = summary.strip()
        summary = summary.replace('"', '').replace("'", '')
        
        return summary

    # 폴백 메서드들 (Ollama 사용 불가 시)
    def _get_default_title(self, content: str) -> str:
        """기본 제목 생성"""
        if not content:
            return "제목 없음"
        
        # 첫 번째 문장에서 제목 추출
        sentences = content.split('.')
        first_sentence = sentences[0].strip()
        
        if len(first_sentence) > 100:
            return first_sentence[:100] + "..."
        
        return first_sentence

    def _get_default_category(self, content: str) -> str:
        """기본 카테고리 분류"""
        if not content:
            return "기타"
        
        # 키워드 기반 분류
        keywords = {
            "가입/계약관리": ["가입", "계약", "체결", "해지", "변경"],
            "보험료관리": ["보험료", "납입", "연체", "환급", "할인"],
            "보험금지급": ["보험금", "지급", "배상", "청구", "지급금"],
            "면책/배상": ["면책", "배상", "책임", "면제", "해제"],
            "사고처리": ["사고", "신고", "조사", "처리", "분쟁"],
            "특약/부가보장": ["특약", "부가보장", "추가보장", "특별약관"]
        }
        
        for category, category_keywords in keywords.items():
            if any(keyword in content for keyword in category_keywords):
                return category
        
        return "기타"

    def _get_default_keywords(self, content: str, max_keywords: int) -> List[str]:
        """기본 키워드 추출"""
        if not content:
            return []
        
        # 보험 관련 키워드
        insurance_keywords = [
            '보험료', '보험금', '면책', '배상', '사고', '계약', '가입', '해지',
            '갱신', '변경', '환급', '할인', '공제', '특약', '부가보장',
            '자동차', '생명', '손해', '건강', '연금', '여행', '재산'
        ]
        
        found_keywords = []
        for keyword in insurance_keywords:
            if keyword in content and len(found_keywords) < max_keywords:
                found_keywords.append(keyword)
        
        return found_keywords

    def _get_default_summary(self, content: str, max_length: int) -> str:
        """기본 요약 생성"""
        if not content:
            return ""
        
        # 첫 번째 문장 추출
        sentences = content.split('.')
        first_sentence = sentences[0].strip()
        
        if len(first_sentence) > max_length:
            return first_sentence[:max_length] + "..."
        
        return first_sentence

    def batch_process(self, contents: List[str], task: str = "title") -> List[Any]:
        """배치 처리"""
        results = []
        
        for i, content in enumerate(contents):
            try:
                if task == "title":
                    result = self.extract_title(content)
                elif task == "category":
                    result = self.classify_category(content)
                elif task == "keywords":
                    result = self.extract_keywords(content)
                elif task == "summary":
                    result = self.generate_summary(content)
                else:
                    result = None
                
                results.append(result)
                
                # 배치 간 딜레이 (로컬 LLM 부하 방지)
                if i < len(contents) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"배치 처리 중 오류 (인덱스 {i}): {e}")
                results.append(None)
        
        return results
