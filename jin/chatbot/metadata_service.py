import logging
import time
from typing import List, Dict, Any, Optional
from django.conf import settings
from .text_preprocessor import TextPreprocessor
from .llm_service import OllamaLLMService

logger = logging.getLogger(__name__)


class MetadataService:
    """메타데이터 통합 처리 서비스"""

    def __init__(self):
        self.text_preprocessor = TextPreprocessor()
        self.llm_service = OllamaLLMService()
        self.category_mapper = InsuranceCategoryMapper()

    def process_document_chunks(
        self, chunks: List[str], document_info: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """문서 청크들을 메타데이터와 함께 처리"""
        results = []

        logger.info(f"메타데이터 처리 시작: {len(chunks)}개 청크")

        for i, chunk_text in enumerate(chunks):
            try:
                # 기본 전처리
                basic_metadata = self.text_preprocessor.process_chunk(
                    chunk_text, i, document_info
                )

                # LLM 기반 메타데이터 생성
                llm_metadata = self._generate_llm_metadata(chunk_text)

                # 통합 메타데이터
                combined_metadata = {**basic_metadata, **llm_metadata}

                # 품질 검증 및 후처리
                final_metadata = self._validate_and_postprocess(combined_metadata)

                results.append(final_metadata)

                # 진행 상황 로깅
                if (i + 1) % 10 == 0:
                    logger.info(f"메타데이터 처리 진행: {i + 1}/{len(chunks)}")

                # 배치 간 딜레이 (LLM 부하 방지)
                if i < len(chunks) - 1:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"청크 {i} 메타데이터 처리 중 오류: {e}")
                # 오류 시 기본 메타데이터만 반환
                error_metadata = self.text_preprocessor.process_chunk(
                    chunk_text, i, document_info
                )
                error_metadata["extraction_method"] = "error"
                error_metadata["confidence_score"] = 0.0
                error_metadata["review_status"] = "error"
                results.append(error_metadata)

        logger.info(f"메타데이터 처리 완료: {len(results)}개 청크")
        return results

    def _generate_llm_metadata(self, content: str) -> Dict[str, Any]:
        """LLM 기반 메타데이터 생성"""
        llm_metadata = {}

        try:
            # 제목 추출
            title = self.llm_service.extract_title(content)
            llm_metadata["title"] = title

            # 카테고리 분류
            category = self.llm_service.classify_category(content)
            llm_metadata["category"] = category

            # 키워드 추출
            keywords = self.llm_service.extract_keywords(content, 5)
            llm_metadata["keywords"] = keywords

            # 요약 생성
            summary = self.llm_service.generate_summary(content, 100)
            llm_metadata["summary"] = summary

            # 추출 방법 및 신뢰도 설정
            llm_metadata["extraction_method"] = "llm_based"
            llm_metadata["confidence_score"] = 0.9  # LLM 기반이므로 높은 신뢰도
            llm_metadata["review_status"] = "pending"

        except Exception as e:
            logger.error(f"LLM 메타데이터 생성 중 오류: {e}")
            # 오류 시 기본값 설정
            llm_metadata = {
                "title": self.llm_service._get_default_title(content),
                "category": self.llm_service._get_default_category(content),
                "keywords": self.llm_service._get_default_keywords(content, 5),
                "summary": self.llm_service._get_default_summary(content, 100),
                "extraction_method": "llm_fallback",
                "confidence_score": 0.5,
                "review_status": "error",
            }

        return llm_metadata

    def _validate_and_postprocess(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 검증 및 후처리"""
        try:
            # 제목 길이 검증
            if metadata.get("title") and len(metadata["title"]) > 500:
                metadata["title"] = metadata["title"][:500] + "..."

            # 카테고리 유효성 검증
            valid_categories = [
                "가입/계약관리",
                "보험료관리",
                "보험금지급",
                "면책/배상",
                "사고처리",
                "특약/부가보장",
                "기타",
            ]
            if metadata.get("category") not in valid_categories:
                metadata["category"] = "기타"

            # 키워드 중복 제거
            if metadata.get("keywords"):
                metadata["keywords"] = list(set(metadata["keywords"]))

            # 요약 길이 검증
            if metadata.get("summary") and len(metadata["summary"]) > 200:
                metadata["summary"] = metadata["summary"][:200] + "..."

            # 신뢰도 점수 조정
            confidence_factors = []

            # 제목 품질 점수
            if metadata.get("title") and len(metadata["title"]) > 10:
                confidence_factors.append(0.2)

            # 카테고리 매칭 점수
            if metadata.get("category") and metadata["category"] != "기타":
                confidence_factors.append(0.2)

            # 키워드 개수 점수
            if metadata.get("keywords") and len(metadata["keywords"]) >= 3:
                confidence_factors.append(0.2)

            # 요약 품질 점수
            if metadata.get("summary") and len(metadata["summary"]) > 20:
                confidence_factors.append(0.2)

            # 조문번호 매칭 점수
            if metadata.get("article_number"):
                confidence_factors.append(0.2)

            # 최종 신뢰도 계산
            if confidence_factors:
                metadata["confidence_score"] = min(1.0, sum(confidence_factors))

            # 검토 상태 설정
            if metadata.get("confidence_score", 0) >= 0.8:
                metadata["review_status"] = "approved"
            elif metadata.get("confidence_score", 0) >= 0.6:
                metadata["review_status"] = "pending"
            else:
                metadata["review_status"] = "needs_review"

            return metadata

        except Exception as e:
            logger.error(f"메타데이터 후처리 중 오류: {e}")
            metadata["confidence_score"] = 0.0
            metadata["review_status"] = "error"
            return metadata

    def batch_process_with_llm(
        self, contents: List[str], task: str = "all"
    ) -> List[Dict[str, Any]]:
        """LLM을 사용한 배치 처리"""
        if task == "all":
            return self.process_document_chunks(contents)
        else:
            return self.llm_service.batch_process(contents, task)

    def generate_metadata(self, content: str) -> Dict[str, Any]:
        """단일 청크에 대한 메타데이터 생성"""
        try:
            # 기본 전처리
            basic_metadata = self.text_preprocessor.process_chunk(content, 0, {})
            
            # LLM 기반 메타데이터 생성
            llm_metadata = self._generate_llm_metadata(content)
            
            # 통합 메타데이터
            combined_metadata = {**basic_metadata, **llm_metadata}
            
            # 품질 검증 및 후처리
            final_metadata = self._validate_and_postprocess(combined_metadata)
            
            return final_metadata
            
        except Exception as e:
            logger.error(f"메타데이터 생성 중 오류: {e}")
            # 오류 시 기본 메타데이터 반환
            return {
                "title": "",
                "category": "기타",
                "keywords": [],
                "summary": "",
                "confidence_score": 0.0,
                "review_status": "error",
                "extraction_method": "error"
            }

    def get_metadata_statistics(
        self, metadata_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """메타데이터 통계 정보 생성"""
        stats = {
            "total_chunks": len(metadata_list),
            "categories": {},
            "confidence_distribution": {
                "high": 0,  # 0.8 이상
                "medium": 0,  # 0.6-0.8
                "low": 0,  # 0.6 미만
            },
            "review_status": {
                "approved": 0,
                "pending": 0,
                "needs_review": 0,
                "error": 0,
            },
            "extraction_methods": {},
            "avg_confidence": 0.0,
        }

        total_confidence = 0.0

        for metadata in metadata_list:
            # 카테고리 통계
            category = metadata.get("category", "기타")
            stats["categories"][category] = stats["categories"].get(category, 0) + 1

            # 신뢰도 분포
            confidence = metadata.get("confidence_score", 0.0)
            total_confidence += confidence

            if confidence >= 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif confidence >= 0.6:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1

            # 검토 상태 통계
            review_status = metadata.get("review_status", "pending")
            stats["review_status"][review_status] = (
                stats["review_status"].get(review_status, 0) + 1
            )

            # 추출 방법 통계
            extraction_method = metadata.get("extraction_method", "unknown")
            stats["extraction_methods"][extraction_method] = (
                stats["extraction_methods"].get(extraction_method, 0) + 1
            )

        # 평균 신뢰도 계산
        if stats["total_chunks"] > 0:
            stats["avg_confidence"] = total_confidence / stats["total_chunks"]

        return stats


class InsuranceCategoryMapper:
    """보험 카테고리 매핑 클래스"""

    def __init__(self):
        self.category_keywords = {
            "가입/계약관리": [
                "가입",
                "계약",
                "체결",
                "해지",
                "변경",
                "갱신",
                "계약자",
                "피보험자",
                "수익자",
                "보험자",
                "계약체결",
                "계약해지",
                "계약변경",
                "계약갱신",
            ],
            "보험료관리": [
                "보험료",
                "납입",
                "연체",
                "환급",
                "할인",
                "공제",
                "보험료납입",
                "보험료연체",
                "보험료환급",
                "보험료할인",
                "보험료공제",
            ],
            "보험금지급": [
                "보험금",
                "지급",
                "배상",
                "청구",
                "지급금",
                "보험금지급",
                "보험금배상",
                "보험금청구",
                "지급조건",
                "지급절차",
                "지급거절",
            ],
            "면책/배상": [
                "면책",
                "배상",
                "책임",
                "면제",
                "해제",
                "면책사유",
                "배상책임",
                "면제사유",
                "책임면제",
                "배상한도",
            ],
            "사고처리": [
                "사고",
                "신고",
                "조사",
                "처리",
                "분쟁",
                "사고신고",
                "사고조사",
                "사고처리",
                "분쟁조정",
                "소송",
                "중재",
            ],
            "특약/부가보장": [
                "특약",
                "부가보장",
                "추가보장",
                "특별약관",
                "부가보험",
                "특약가입",
                "부가보장가입",
                "추가보장가입",
            ],
        }

    def map_category(self, text: str) -> str:
        """텍스트를 카테고리로 매핑"""
        if not text:
            return "기타"

        text_lower = text.lower()
        category_scores = {}

        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            if score > 0:
                category_scores[category] = score

        if category_scores:
            # 가장 높은 점수의 카테고리 반환
            return max(category_scores, key=category_scores.get)

        return "기타"

    def get_category_keywords(self, category: str) -> List[str]:
        """카테고리별 키워드 반환"""
        return self.category_keywords.get(category, [])

    def get_all_categories(self) -> List[str]:
        """모든 카테고리 목록 반환"""
        return list(self.category_keywords.keys()) + ["기타"]
