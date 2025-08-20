import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q
from .models import DocumentChunk
from .keyword_mapper import KeywordMapper
from .metadata_service import MetadataService

logger = logging.getLogger(__name__)


class EnhancedSearchService:
    """메타데이터 기반 향상된 검색 서비스"""

    def __init__(self, document_service, embedding_service):
        self.document_service = document_service
        self.embedding_service = embedding_service
        self.keyword_mapper = KeywordMapper()
        self.metadata_service = MetadataService()

        # 검색 가중치 설정
        self.vector_weight = 0.5
        self.keyword_weight = 0.3
        self.metadata_weight = 0.2

        # 검색 파라미터
        self.top_k = 15
        self.similarity_threshold = 0.3
        self.max_context_length = 3000

    def enhanced_search(
        self, 
        query: str, 
        category_filter: Optional[str] = None,
        insurance_company: Optional[str] = None,
        article_number: Optional[int] = None,
        use_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        향상된 검색 수행: 벡터 + 키워드 + 메타데이터 필터링
        """
        logger.info(f"향상된 검색 시작: {query}")
        logger.info(f"필터: 카테고리={category_filter}, 보험사={insurance_company}, 조문={article_number}")

        # 1. 쿼리 전처리 및 키워드 매핑
        processed_query = self._preprocess_query(query)
        
        # 2. 카테고리 자동 감지 (필터가 없는 경우)
        if not category_filter:
            category_filter = self._detect_category(processed_query)

        # 3. 벡터 검색
        vector_results = self._vector_search(processed_query)
        
        # 4. 키워드 검색
        keyword_results = self._keyword_search(processed_query)
        
        # 5. 메타데이터 기반 필터링
        if use_metadata:
            filtered_results = self._apply_metadata_filters(
                vector_results + keyword_results,
                category_filter,
                insurance_company,
                article_number
            )
        else:
            filtered_results = vector_results + keyword_results

        # 6. 결과 통합 및 재순위화
        combined_results = self._combine_and_rerank(filtered_results, processed_query)
        
        # 7. 최종 정렬 및 반환
        final_results = self._final_sort(combined_results)
        
        logger.info(f"향상된 검색 완료: {len(final_results)}개 결과")
        return final_results

    def _preprocess_query(self, query: str) -> str:
        """쿼리 전처리 및 키워드 매핑"""
        try:
            # 키워드 매핑 적용
            mapped_query = self.keyword_mapper.map_keywords(query)
            
            # 특수문자 정리
            cleaned_query = re.sub(r'[^\w\s가-힣]', ' ', mapped_query)
            cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
            
            logger.info(f"쿼리 전처리: {query} -> {cleaned_query}")
            return cleaned_query
            
        except Exception as e:
            logger.error(f"쿼리 전처리 오류: {e}")
            return query

    def _detect_category(self, query: str) -> Optional[str]:
        """쿼리에서 카테고리 자동 감지"""
        try:
            # 키워드 기반 카테고리 감지
            category_keywords = {
                "가입/계약관리": ["가입", "계약", "체결", "해지", "변경", "갱신"],
                "보험료관리": ["보험료", "납입", "연체", "환급", "할인", "공제"],
                "보험금지급": ["보험금", "지급", "배상", "청구", "지급금"],
                "면책/배상": ["면책", "배상", "책임", "면제", "해제"],
                "사고처리": ["사고", "신고", "조사", "처리", "분쟁"],
                "특약/부가보장": ["특약", "부가보장", "추가보장", "특별약관"]
            }
            
            query_lower = query.lower()
            category_scores = {}
            
            for category, keywords in category_keywords.items():
                score = sum(1 for keyword in keywords if keyword in query_lower)
                if score > 0:
                    category_scores[category] = score
            
            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                logger.info(f"감지된 카테고리: {best_category}")
                return best_category
            
            return None
            
        except Exception as e:
            logger.error(f"카테고리 감지 오류: {e}")
            return None

    def _vector_search(self, query: str) -> List[Dict[str, Any]]:
        """벡터 유사도 검색"""
        try:
            vector_results = self.document_service.search_similar_chunks(
                query=query, top_k=self.top_k
            )
            
            # 메타데이터 추가
            for result in vector_results:
                result["search_type"] = "vector"
                result["weighted_score"] = result.get("score", 0) * self.vector_weight
                
                # 메타데이터 정보 추가
                chunk_id = result.get("metadata", {}).get("chunk_id")
                if chunk_id:
                    try:
                        chunk = DocumentChunk.objects.get(id=chunk_id)
                        result["metadata"].update({
                            "title": chunk.title,
                            "category": chunk.category,
                            "article_number": chunk.article_number,
                            "keywords": chunk.keywords,
                            "summary": chunk.summary
                        })
                    except DocumentChunk.DoesNotExist:
                        pass
            
            logger.info(f"벡터 검색 결과: {len(vector_results)}개")
            return vector_results
            
        except Exception as e:
            logger.error(f"벡터 검색 오류: {e}")
            return []

    def _keyword_search(self, query: str) -> List[Dict[str, Any]]:
        """키워드 매칭 검색"""
        try:
            # 쿼리에서 키워드 추출
            keywords = self.keyword_mapper.extract_keywords_from_text(query)
            
            if not keywords:
                return []
            
            # 메타데이터 기반 키워드 검색
            keyword_results = []
            
            # 키워드별로 검색
            for keyword in keywords:
                if len(keyword.strip()) >= 2:
                    # 제목, 카테고리, 키워드 필드에서 검색
                    chunks = DocumentChunk.objects.filter(
                        Q(title__icontains=keyword) |
                        Q(category__icontains=keyword) |
                        Q(keywords__contains=keyword) |
                        Q(chunk_text__icontains=keyword)
                    ).select_related("document", "document__insurance_company")
                    
                    for chunk in chunks:
                        # 키워드 매칭 점수 계산
                        score = self._calculate_keyword_score(chunk, keyword)
                        
                        if score > 0:
                            result = {
                                "chunk_id": chunk.id,
                                "content": chunk.chunk_text,
                                "document_id": chunk.document.id,
                                "document_title": chunk.document.title,
                                "score": score,
                                "search_type": "keyword",
                                "weighted_score": score * self.keyword_weight,
                                "matched_keyword": keyword,
                                "metadata": {
                                    "content": chunk.chunk_text,
                                    "document_id": chunk.document.id,
                                    "chunk_id": chunk.id,
                                    "title": chunk.title,
                                    "category": chunk.category,
                                    "article_number": chunk.article_number,
                                    "keywords": chunk.keywords,
                                    "summary": chunk.summary
                                }
                            }
                            keyword_results.append(result)
            
            # 중복 제거 및 정렬
            unique_results = {}
            for result in keyword_results:
                chunk_id = result["chunk_id"]
                if chunk_id not in unique_results or result["score"] > unique_results[chunk_id]["score"]:
                    unique_results[chunk_id] = result
            
            keyword_results = list(unique_results.values())
            keyword_results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.info(f"키워드 검색 결과: {len(keyword_results)}개")
            return keyword_results[:self.top_k]
            
        except Exception as e:
            logger.error(f"키워드 검색 오류: {e}")
            return []

    def _calculate_keyword_score(self, chunk: DocumentChunk, keyword: str) -> float:
        """키워드 매칭 점수 계산"""
        score = 0.0
        keyword_lower = keyword.lower()
        
        # 제목에서 매칭 (가장 높은 가중치)
        if chunk.title and keyword_lower in chunk.title.lower():
            score += 3.0
        
        # 카테고리에서 매칭
        if chunk.category and keyword_lower in chunk.category.lower():
            score += 2.0
        
        # 키워드 리스트에서 매칭
        if chunk.keywords:
            for kw in chunk.keywords:
                if keyword_lower in kw.lower():
                    score += 1.5
                    break
        
        # 내용에서 매칭
        if keyword_lower in chunk.chunk_text.lower():
            score += 1.0
        
        return score

    def _apply_metadata_filters(
        self, 
        results: List[Dict[str, Any]], 
        category_filter: Optional[str] = None,
        insurance_company: Optional[str] = None,
        article_number: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """메타데이터 기반 필터링"""
        try:
            filtered_results = []
            
            for result in results:
                metadata = result.get("metadata", {})
                include_result = True
                
                # 카테고리 필터
                if category_filter and metadata.get("category"):
                    if category_filter.lower() not in metadata["category"].lower():
                        include_result = False
                
                # 보험사 필터
                if insurance_company and result.get("document_title"):
                    if insurance_company.lower() not in result["document_title"].lower():
                        include_result = False
                
                # 조문번호 필터
                if article_number and metadata.get("article_number"):
                    if metadata["article_number"] != article_number:
                        include_result = False
                
                if include_result:
                    filtered_results.append(result)
            
            logger.info(f"메타데이터 필터링: {len(results)} -> {len(filtered_results)}개")
            return filtered_results
            
        except Exception as e:
            logger.error(f"메타데이터 필터링 오류: {e}")
            return results

    def _combine_and_rerank(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """결과 통합 및 재순위화"""
        try:
            # 중복 제거
            unique_results = {}
            for result in results:
                chunk_id = result.get("chunk_id")
                if chunk_id not in unique_results:
                    unique_results[chunk_id] = result
                else:
                    # 더 높은 점수를 가진 결과 유지
                    current_score = unique_results[chunk_id].get("weighted_score", 0)
                    new_score = result.get("weighted_score", 0)
                    if new_score > current_score:
                        unique_results[chunk_id] = result
            
            # 메타데이터 기반 점수 조정
            for result in unique_results.values():
                metadata_score = self._calculate_metadata_score(result, query)
                result["metadata_score"] = metadata_score
                result["final_score"] = result.get("weighted_score", 0) + metadata_score
            
            return list(unique_results.values())
            
        except Exception as e:
            logger.error(f"결과 통합 오류: {e}")
            return results

    def _calculate_metadata_score(self, result: Dict[str, Any], query: str) -> float:
        """메타데이터 기반 점수 계산"""
        try:
            metadata = result.get("metadata", {})
            score = 0.0
            
            # 제목 관련성 점수
            title = metadata.get("title", "")
            if title and any(word in title.lower() for word in query.lower().split()):
                score += 0.3
            
            # 카테고리 관련성 점수
            category = metadata.get("category", "")
            if category and category != "기타":
                score += 0.2
            
            # 키워드 매칭 점수
            keywords = metadata.get("keywords", [])
            if keywords:
                query_words = query.lower().split()
                keyword_matches = sum(1 for kw in keywords if any(word in kw.lower() for word in query_words))
                score += min(keyword_matches * 0.1, 0.3)
            
            # 요약 관련성 점수
            summary = metadata.get("summary", "")
            if summary and any(word in summary.lower() for word in query.lower().split()):
                score += 0.1
            
            return score * self.metadata_weight
            
        except Exception as e:
            logger.error(f"메타데이터 점수 계산 오류: {e}")
            return 0.0

    def _final_sort(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """최종 정렬"""
        try:
            # 최종 점수 기준으로 정렬
            sorted_results = sorted(
                results, 
                key=lambda x: x.get("final_score", 0), 
                reverse=True
            )
            
            # 상위 결과만 반환
            return sorted_results[:self.top_k]
            
        except Exception as e:
            logger.error(f"최종 정렬 오류: {e}")
            return results

    def build_enhanced_context(self, search_results: List[Dict[str, Any]]) -> str:
        """향상된 컨텍스트 구축"""
        if not search_results:
            return "관련 문서를 찾을 수 없습니다."
        
        try:
            context_parts = []
            total_length = 0
            
            for i, result in enumerate(search_results, 1):
                content = result.get("content", "")
                final_score = result.get("final_score", 0)
                document_title = result.get("document_title", "알 수 없는 문서")
                metadata = result.get("metadata", {})
                
                # 내용이 비어있으면 건너뛰기
                if not content or len(content.strip()) < 10:
                    continue
                
                # 내용 길이 제한
                if len(content) > 400:
                    content = content[:400] + "..."
                
                # 메타데이터 정보 포함
                metadata_info = []
                if metadata.get("title"):
                    metadata_info.append(f"제목: {metadata['title']}")
                if metadata.get("category"):
                    metadata_info.append(f"카테고리: {metadata['category']}")
                if metadata.get("article_number"):
                    metadata_info.append(f"조문: {metadata['article_number']}")
                
                metadata_str = " | ".join(metadata_info) if metadata_info else ""
                
                # 컨텍스트 구성
                chunk_text = f"[{i}] {document_title} (점수: {final_score:.2f})"
                if metadata_str:
                    chunk_text += f" | {metadata_str}"
                chunk_text += f"\n{content}\n"
                
                if total_length + len(chunk_text) > self.max_context_length:
                    break
                
                context_parts.append(chunk_text)
                total_length += len(chunk_text)
            
            if not context_parts:
                return "관련 문서를 찾을 수 없습니다."
            
            context = "\n".join(context_parts)
            logger.info(f"향상된 컨텍스트 길이: {len(context)}자")
            
            return context
            
        except Exception as e:
            logger.error(f"향상된 컨텍스트 구축 오류: {e}")
            return "컨텍스트 구축 중 오류가 발생했습니다."

    def get_search_statistics(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """검색 통계 정보"""
        try:
            stats = {
                "total_results": len(search_results),
                "search_types": {},
                "categories": {},
                "score_distribution": {
                    "high": 0,    # 0.8 이상
                    "medium": 0,  # 0.5-0.8
                    "low": 0      # 0.5 미만
                },
                "avg_score": 0.0
            }
            
            total_score = 0.0
            
            for result in search_results:
                # 검색 유형 통계
                search_type = result.get("search_type", "unknown")
                stats["search_types"][search_type] = stats["search_types"].get(search_type, 0) + 1
                
                # 카테고리 통계
                category = result.get("metadata", {}).get("category", "기타")
                stats["categories"][category] = stats["categories"].get(category, 0) + 1
                
                # 점수 분포
                final_score = result.get("final_score", 0.0)
                total_score += final_score
                
                if final_score >= 0.8:
                    stats["score_distribution"]["high"] += 1
                elif final_score >= 0.5:
                    stats["score_distribution"]["medium"] += 1
                else:
                    stats["score_distribution"]["low"] += 1
            
            # 평균 점수 계산
            if stats["total_results"] > 0:
                stats["avg_score"] = total_score / stats["total_results"]
            
            return stats
            
        except Exception as e:
            logger.error(f"검색 통계 생성 오류: {e}")
            return {"error": str(e)}
