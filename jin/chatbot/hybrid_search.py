import re
from typing import List, Dict, Any, Tuple, Optional
import logging
from .keyword_expansion import KeywordExpansionService
from .models import DocumentChunk

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    벡터 유사도 검색과 키워드 매칭 검색을 결합한 하이브리드 검색 서비스
    """

    def __init__(self, document_service, embedding_service):
        self.document_service = document_service
        self.embedding_service = embedding_service
        self.keyword_service = KeywordExpansionService()

        # 검색 가중치 설정 (연락처 관련 질문에 최적화)
        self.vector_weight = 0.6  # 벡터 검색 가중치
        self.keyword_weight = 0.4  # 키워드 검색 가중치

        # 검색 파라미터 (신뢰도 향상)
        self.top_k = 10  # 검색 결과 개수 최적화
        self.similarity_threshold = 0.7  # 벡터 유사도 임계값 상향
        self.max_context_length = 3000  # 컨텍스트 길이 최적화
        
        # 신뢰도 점수 설정
        self.min_confidence_score = 0.5  # 최소 신뢰도 점수

    def hybrid_search(self, query: str) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 수행: 벡터 검색 + 키워드 검색 + 보험사명 매칭 강화
        """
        logger.info(f"하이브리드 검색 시작: {query}")

        # 1. 보험사명 매칭 강화
        company_boost = self._detect_company_query(query)
        
        # 2. 키워드 확장
        expanded_keywords = self.keyword_service.get_relevant_keywords(query, top_n=5)
        logger.info(f"확장된 키워드: {expanded_keywords}")

        # 3. 벡터 검색 수행
        vector_results = self._vector_search(query)
        logger.info(f"벡터 검색 결과: {len(vector_results)}개")

        # 4. 키워드 검색 수행
        keyword_results = self._keyword_search(expanded_keywords)
        logger.info(f"키워드 검색 결과: {len(keyword_results)}개")

        # 5. 보험사명 매칭 결과 추가
        if company_boost:
            company_results = self._company_specific_search(company_boost, query)
            logger.info(f"보험사명 매칭 결과: {len(company_results)}개")
            keyword_results.extend(company_results)

        # 6. 결과 통합 및 가중치 적용
        combined_results = self._combine_results(vector_results, keyword_results)
        logger.info(f"통합 결과: {len(combined_results)}개")

        # 7. 중복 제거 및 정렬
        final_results = self._deduplicate_and_sort(combined_results)
        logger.info(f"최종 결과: {len(final_results)}개")

        return final_results

    def _detect_company_query(self, query: str) -> Optional[str]:
        """
        질문에서 보험사명 감지
        """
        company_patterns = {
            r'DB손해보험|프로미카': 'DB손해보험',
            r'한화손해보험|한화': '한화손해보험',
            r'현대해상화재|현대해상': '현대해상화재',
            r'메리츠화재|메리츠': '메리츠화재',
            r'롯데손해보험|롯데': '롯데손해보험'
        }
        
        for pattern, company in company_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                return company
        return None

    def _company_specific_search(self, company_name: str, query: str) -> List[Dict[str, Any]]:
        """
        특정 보험사 관련 문서 검색
        """
        try:
            # 해당 보험사의 문서만 검색
            company_chunks = DocumentChunk.objects.filter(
                document__insurance_company__name__icontains=company_name
            ).select_related('document', 'document__insurance_company')
            
            results = []
            for chunk in company_chunks[:20]:  # 상위 20개만
                # 키워드 매칭 점수 계산
                chunk_text_lower = chunk.chunk_text.lower()
                query_lower = query.lower()
                
                # 연락처 관련 키워드 매칭
                contact_keywords = ['연락처', '전화번호', '고객센터', '상담', '문의']
                contact_score = sum(1 for keyword in contact_keywords if keyword in chunk_text_lower)
                
                if contact_score > 0:
                    results.append({
                        "chunk_id": chunk.id,
                        "content": chunk.chunk_text,
                        "document_id": chunk.document.id,
                        "document_title": chunk.document.title,
                        "score": contact_score * 0.5,  # 보험사 매칭 보너스
                        "search_type": "company_specific",
                        "weighted_score": contact_score * 0.5 * self.keyword_weight,
                        "metadata": {
                            "content": chunk.chunk_text,
                            "document_id": chunk.document.id,
                            "chunk_id": chunk.id,
                        },
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"보험사별 검색 오류: {e}")
            return []

    def _vector_search(self, query: str) -> List[Dict[str, Any]]:
        """
        벡터 유사도 검색 수행
        """
        try:
            # 기존 벡터 검색 사용
            vector_results = self.document_service.search_similar_chunks(
                query=query, top_k=self.top_k
            )

            # 유사도 임계값 필터링
            filtered_results = []
            for result in vector_results:
                score = result.get("score", 0)
                if score >= self.similarity_threshold:
                    result["search_type"] = "vector"
                    result["weighted_score"] = score * self.vector_weight
                    filtered_results.append(result)

            logger.info(
                f"벡터 검색 필터링 결과: {len(filtered_results)}개 (임계값: {self.similarity_threshold})"
            )
            return filtered_results

        except Exception as e:
            logger.error(f"벡터 검색 오류: {e}")
            return []

    def _keyword_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        키워드 매칭 검색 수행 (데이터베이스 쿼리 최적화)
        """
        try:
            keyword_results = []
            
            # 데이터베이스에서 키워드가 포함된 청크들을 효율적으로 검색
            from django.db.models import Q
            
            # 키워드별로 OR 조건으로 검색
            query = Q()
            for keyword in keywords:
                if len(keyword.strip()) >= 2:  # 2글자 이상만 검색
                    query |= Q(chunk_text__icontains=keyword.strip())
            
            # 키워드가 포함된 청크들만 가져오기
            matching_chunks = DocumentChunk.objects.filter(query).select_related('document')
            
            logger.info(f"키워드 매칭 청크 수: {matching_chunks.count()}")
            
            for chunk in matching_chunks:
                chunk_text = chunk.chunk_text.lower()
                chunk_score = 0
                matched_keywords = []

                for keyword in keywords:
                    keyword_lower = keyword.lower().strip()
                    
                    if len(keyword_lower) < 2:
                        continue

                    # 정확한 키워드 매칭
                    if keyword_lower in chunk_text:
                        chunk_score += 1.0
                        matched_keywords.append(keyword)

                    # 부분 키워드 매칭 (단어 단위)
                    else:
                        keyword_parts = keyword_lower.split()
                        for part in keyword_parts:
                            if len(part) >= 2 and part in chunk_text:
                                chunk_score += 0.5
                                matched_keywords.append(part)

                if chunk_score > 0:
                    # 키워드 검색 결과 생성
                    result = {
                        "chunk_id": chunk.id,
                        "content": chunk.chunk_text,
                        "document_id": chunk.document.id,
                        "document_title": chunk.document.title,
                        "score": chunk_score,
                        "search_type": "keyword",
                        "weighted_score": chunk_score * self.keyword_weight,
                        "matched_keywords": matched_keywords,
                        "metadata": {
                            "content": chunk.chunk_text,
                            "document_id": chunk.document.id,
                            "chunk_id": chunk.id,
                        },
                    }
                    keyword_results.append(result)

            # 점수 기준으로 정렬
            keyword_results.sort(key=lambda x: x["score"], reverse=True)

            logger.info(f"키워드 검색 결과: {len(keyword_results)}개")
            return keyword_results[: self.top_k]

        except Exception as e:
            logger.error(f"키워드 검색 오류: {e}")
            return []

    def _combine_results(
        self, vector_results: List[Dict], keyword_results: List[Dict]
    ) -> List[Dict]:
        """
        벡터 검색과 키워드 검색 결과 통합
        """
        combined = []

        # 벡터 검색 결과 추가
        for result in vector_results:
            combined.append(result)

        # 키워드 검색 결과 추가 (중복 체크)
        for keyword_result in keyword_results:
            chunk_id = keyword_result["chunk_id"]

            # 이미 벡터 검색 결과에 있는지 확인
            existing = next(
                (r for r in combined if r.get("chunk_id") == chunk_id), None
            )

            if existing:
                # 기존 결과에 키워드 점수 추가
                existing["weighted_score"] += keyword_result["weighted_score"]
                existing["search_types"] = existing.get(
                    "search_types", [existing["search_type"]]
                ) + ["keyword"]
                if "matched_keywords" in keyword_result:
                    existing["matched_keywords"] = keyword_result["matched_keywords"]
            else:
                # 새로운 결과 추가
                combined.append(keyword_result)

        return combined

    def _deduplicate_and_sort(self, results: List[Dict]) -> List[Dict]:
        """
        중복 제거, 신뢰도 점수 계산 및 정렬
        """
        # chunk_id 기준으로 중복 제거
        unique_results = {}
        for result in results:
            chunk_id = result.get("chunk_id")
            if chunk_id not in unique_results:
                unique_results[chunk_id] = result
            else:
                # 더 높은 점수를 가진 결과 유지
                if result.get("weighted_score", 0) > unique_results[chunk_id].get(
                    "weighted_score", 0
                ):
                    unique_results[chunk_id] = result

        # 신뢰도 점수 계산 및 필터링
        confidence_filtered_results = []
        for result in unique_results.values():
            confidence_score = self._calculate_confidence_score(result)
            result["confidence_score"] = confidence_score
            
            # 최소 신뢰도 점수 이상인 결과만 포함
            if confidence_score >= self.min_confidence_score:
                confidence_filtered_results.append(result)

        # 신뢰도 점수 기준으로 정렬
        sorted_results = sorted(
            confidence_filtered_results,
            key=lambda x: x.get("confidence_score", 0),
            reverse=True,
        )

        return sorted_results[: self.top_k]

    def _calculate_confidence_score(self, result: Dict) -> float:
        """
        검색 결과의 신뢰도 점수 계산
        """
        base_score = result.get("weighted_score", 0)
        search_type = result.get("search_type", "unknown")
        
        # 검색 유형별 가중치
        type_weights = {
            "vector": 1.0,
            "keyword": 0.8,
            "hybrid": 1.2,
            "company_specific": 1.1
        }
        
        # 검색 유형 가중치 적용
        type_weight = type_weights.get(search_type, 1.0)
        
        # 키워드 매칭 점수 (키워드 검색의 경우)
        keyword_bonus = 0.0
        if search_type == "keyword" and "matched_keywords" in result:
            matched_count = len(result["matched_keywords"])
            keyword_bonus = min(matched_count * 0.1, 0.3)  # 최대 0.3점 보너스
        
        # 최종 신뢰도 점수 계산
        confidence_score = (base_score * type_weight) + keyword_bonus
        
        # 0.0 ~ 1.0 범위로 정규화
        confidence_score = min(max(confidence_score, 0.0), 1.0)
        
        return confidence_score

    def build_enhanced_context(self, search_results: List[Dict]) -> str:
        """
        검색 결과를 바탕으로 향상된 컨텍스트 구축
        """
        if not search_results:
            return "관련 문서를 찾을 수 없습니다."

        context_parts = []
        total_length = 0

        for i, result in enumerate(search_results, 1):
            content = result.get("content", "")
            confidence_score = result.get("confidence_score", 0)
            document_title = result.get("document_title", "알 수 없는 문서")

            # 내용이 비어있으면 건너뛰기
            if not content or len(content.strip()) < 10:
                continue

            # 내용 길이 제한 (각 청크당 최대 400자로 최적화)
            if len(content) > 400:
                content = content[:400] + "..."

            # 검색 유형과 신뢰도 점수 정보 포함
            chunk_text = f"[{i}] {document_title} (신뢰도: {confidence_score:.2f})\n{content}\n"

            if total_length + len(chunk_text) > self.max_context_length:
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        if not context_parts:
            return "관련 문서를 찾을 수 없습니다."

        context = "\n".join(context_parts)
        logger.info(f"컨텍스트 길이: {len(context)}자")

        return context
