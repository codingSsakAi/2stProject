import os
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.core.exceptions import ValidationError
import numpy as np
import requests
import json
from django.utils import timezone
from .models import DocumentChunk
from .hybrid_search import HybridSearchService
from .contact_info_service import ContactInfoService
from .cache_service import CacheService
from .insurance_service import InsuranceRecommendationService
from .ml_models import InsurancePremiumPredictor, CustomerBehaviorAnalyzer

# Pinecone 클라이언트
try:
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logging.warning("Pinecone 클라이언트를 사용할 수 없습니다.")

# Sentence Transformers
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("Sentence Transformers를 사용할 수 없습니다.")

logger = logging.getLogger(__name__)


class EmbeddingService:
    """텍스트 Embedding 생성 서비스"""

    def __init__(self):
        self.model = None
        self.upstage_api_key = getattr(settings, "UPSTAGE_API_KEY", None)
        self._initialize_model()

    def _initialize_model(self):
        """Embedding 모델 초기화"""
        self.model = None

        # Sentence Transformers를 기본으로 사용 (안정성 우선)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info("Sentence Transformers 모델 로딩 시작...")
                self.model = SentenceTransformer(
                    "sentence-transformers/all-mpnet-base-v2"
                )
                logger.info("Sentence Transformers 모델 로드 완료")
            except Exception as e:
                logger.error(f"Sentence Transformers 모델 로드 실패: {e}")
                self.model = None

        # Upstage API 키 확인 (선택적 사용)
        if self.upstage_api_key:
            logger.info(
                f"Upstage Embedding API 키 확인됨 - API 키: {self.upstage_api_key[:10]}..."
            )
        else:
            logger.info("Upstage API 키가 없습니다.")

        # 최종 상태 확인
        if self.model:
            logger.info("✅ Embedding 모델 초기화 성공: Sentence Transformers")
        elif self.upstage_api_key:
            logger.info("⚠️ Embedding 모델: Upstage API만 사용 가능")
        else:
            logger.error("❌ 사용 가능한 Embedding 모델이 없습니다.")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """텍스트 리스트를 Embedding 벡터로 변환"""
        if not texts:
            return []

        try:
            # Sentence Transformers 우선 사용 (안정성)
            if self.model:
                logger.info("Sentence Transformers로 Embedding 생성 시작...")
                return self._get_sentence_transformers_embeddings(texts)

            # Upstage API는 백업으로만 사용
            elif self.upstage_api_key:
                logger.info("Upstage API로 Embedding 생성 시작...")
                try:
                    return self._get_upstage_embeddings(texts)
                except Exception as e:
                    logger.error(f"Upstage API 실패: {e}")
                    raise Exception("사용 가능한 Embedding 모델이 없습니다.")

            else:
                raise Exception("사용 가능한 Embedding 모델이 없습니다.")

        except Exception as e:
            logger.error(f"Embedding 생성 실패: {e}")
            raise

    def _expand_embedding_to_4096(self, embedding: List[float]) -> List[float]:
        """768차원 벡터를 4096차원으로 확장"""
        if len(embedding) != 768:
            raise ValueError(f"예상된 768차원이 아닙니다: {len(embedding)}차원")

        # 768차원을 4096차원으로 확장하는 방법
        # 방법 1: 반복 및 보간
        expanded = []
        for i in range(4096):
            source_idx = i % 768
            expanded.append(embedding[source_idx])

        # 방법 2: 0으로 패딩 (더 간단하지만 성능은 떨어질 수 있음)
        # expanded = embedding + [0.0] * (4096 - 768)

        return expanded

    def _get_upstage_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Upstage Embedding API를 사용하여 벡터 생성"""
        try:
            url = "https://api.upstage.ai/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {self.upstage_api_key}",
                "Content-Type": "application/json",
            }

            # 지원되는 모델로 변경 (올바른 모델명 사용)
            data = {"input": texts, "model": "solar-embedding-1-large"}

            logger.info(f"Upstage API 호출 시작: {len(texts)}개 텍스트")
            logger.info(f"API URL: {url}")
            logger.info(f"모델: {data['model']}")

            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            embeddings = []

            for item in result.get("data", []):
                embedding = item.get("embedding", [])
                embeddings.append(embedding)
                logger.info(f"생성된 벡터 차원: {len(embedding)}")

            logger.info(f"총 {len(embeddings)}개의 벡터 생성 완료")
            return embeddings

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.warning(
                    f"Upstage API 모델 오류, Sentence Transformers로 전환: {e}"
                )
                # 모델 오류 시 Sentence Transformers로 fallback
                return self._get_sentence_transformers_embeddings(texts)
            else:
                raise
        except Exception as e:
            logger.error(f"Upstage API 호출 실패: {e}")
            logger.error(
                f"응답 내용: {response.text if 'response' in locals() else 'N/A'}"
            )
            # 기타 오류 시에도 Sentence Transformers로 fallback
            return self._get_sentence_transformers_embeddings(texts)

    def _get_sentence_transformers_embeddings(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Sentence Transformers를 사용하여 Embedding 생성"""
        if not self.model:
            logger.error("Sentence Transformers 모델이 로드되지 않았습니다.")
            raise Exception("Sentence Transformers 모델이 로드되지 않았습니다.")

        try:
            logger.info(f"Sentence Transformers 인코딩 시작: {len(texts)}개 텍스트")
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            embeddings_list = embeddings.tolist()
            logger.info(f"인코딩 완료: {len(embeddings_list)}개 벡터 (768차원)")

            # 768차원을 4096차원으로 확장
            expanded_embeddings = []
            for i, embedding in enumerate(embeddings_list):
                try:
                    expanded = self._expand_embedding_to_4096(embedding)
                    expanded_embeddings.append(expanded)
                except Exception as e:
                    logger.error(f"벡터 {i} 확장 실패: {e}")
                    raise

            logger.info(
                f"✅ Sentence Transformers로 {len(embeddings_list)}개 벡터 생성 완료 (768→4096차원 확장)"
            )
            return expanded_embeddings
        except Exception as e:
            logger.error(f"Sentence Transformers Embedding 생성 실패: {e}")
            raise

    def get_single_embedding(self, text: str) -> List[float]:
        """단일 텍스트를 Embedding 벡터로 변환"""
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else []


class PineconeService:
    """Pinecone 벡터 데이터베이스 서비스"""

    def __init__(self):
        self.pc = None
        self.index = None
        self.index_name = getattr(
            settings, "PINECONE_INDEX_NAME", "insurance-documents"
        )
        self.dimension = getattr(settings, "PINECONE_DIMENSION", 4096)
        self.metric = getattr(settings, "PINECONE_METRIC", "cosine")
        self._initialize_pinecone()

    def _initialize_pinecone(self):
        """Pinecone 초기화 및 인덱스 설정"""
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone 클라이언트를 사용할 수 없습니다.")
            return

        try:
            # Pinecone 클라이언트 초기화
            self.pc = Pinecone(api_key=getattr(settings, "PINECONE_API_KEY", ""))

            # 인덱스 존재 확인 및 생성
            if self.index_name not in self.pc.list_indexes().names():
                self._create_index()

            # 인덱스 연결
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Pinecone 인덱스 '{self.index_name}' 연결 완료")

        except Exception as e:
            logger.error(f"Pinecone 초기화 실패: {e}")
            raise

    def _create_index(self):
        """Pinecone 인덱스 생성"""
        try:
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=self.metric,
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Pinecone 인덱스 '{self.index_name}' 생성 완료")
        except Exception as e:
            logger.error(f"Pinecone 인덱스 생성 실패: {e}")
            raise

    def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """벡터들을 Pinecone에 업로드"""
        if not self.index:
            logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
            return False

        try:
            # 벡터 데이터 준비
            upsert_data = []
            for vector_data in vectors:
                upsert_data.append(
                    {
                        "id": vector_data["id"],
                        "values": vector_data["values"],
                        "metadata": vector_data.get("metadata", {}),
                    }
                )

            # 배치 업로드 (최대 100개씩)
            batch_size = 100
            for i in range(0, len(upsert_data), batch_size):
                batch = upsert_data[i : i + batch_size]
                self.index.upsert(vectors=batch)

            logger.info(f"{len(vectors)}개의 벡터를 Pinecone에 업로드 완료")
            return True

        except Exception as e:
            logger.error(f"Pinecone 벡터 업로드 실패: {e}")
            return False

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """유사한 벡터 검색"""
        if not self.index:
            logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
            return []

        try:
            search_params = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": True,
            }

            if filter_dict:
                search_params["filter"] = filter_dict

            results = self.index.query(**search_params)

            # 결과 정리
            matches = []
            for match in results.get("matches", []):
                matches.append(
                    {
                        "id": match["id"],
                        "score": match["score"],
                        "metadata": match.get("metadata", {}),
                    }
                )

            return matches

        except Exception as e:
            logger.error(f"Pinecone 벡터 검색 실패: {e}")
            return []

    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """벡터 삭제"""
        if not self.index:
            logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
            return False

        try:
            self.index.delete(ids=vector_ids)
            logger.info(f"{len(vector_ids)}개의 벡터를 Pinecone에서 삭제 완료")
            return True

        except Exception as e:
            logger.error(f"Pinecone 벡터 삭제 실패: {e}")
            return False

    def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보 조회"""
        if not self.index:
            return {}

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "index_fullness": stats.get("index_fullness", 0),
                "namespaces": stats.get("namespaces", {}),
            }
        except Exception as e:
            logger.error(f"Pinecone 인덱스 통계 조회 실패: {e}")
            return {}


class DocumentEmbeddingService:
    """문서 Embedding 처리 통합 서비스"""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()

    def process_document_chunks(self, document_chunks: List[Dict[str, Any]]) -> bool:
        """문서 청크들을 Embedding 처리하고 Pinecone에 업로드"""
        try:
            # 텍스트 추출
            texts = [chunk["content"] for chunk in document_chunks]

            # Embedding 생성
            embeddings = self.embedding_service.get_embeddings(texts)

            if len(embeddings) != len(document_chunks):
                raise Exception("Embedding 개수와 청크 개수가 일치하지 않습니다.")

            # Pinecone 업로드용 벡터 데이터 준비
            vectors = []
            for i, chunk in enumerate(document_chunks):
                vector_data = {
                    "id": f"chunk_{chunk['id']}",
                    "values": embeddings[i],
                    "metadata": {
                        "document_id": chunk["document_id"],
                        "chunk_index": chunk["chunk_index"],
                        "content": chunk["content"][
                            :1000
                        ],  # 메타데이터에는 일부만 저장
                        "insurance_company": chunk.get("insurance_company", ""),
                        "document_title": chunk.get("document_title", ""),
                        "created_at": chunk.get("created_at", ""),
                        "chunk_type": "document",
                    },
                }
                vectors.append(vector_data)

            # Pinecone에 업로드
            success = self.pinecone_service.upsert_vectors(vectors)

            if success:
                logger.info(f"{len(vectors)}개의 문서 청크를 성공적으로 처리했습니다.")

            return success

        except Exception as e:
            logger.error(f"문서 청크 Embedding 처리 실패: {e}")
            return False

    def search_similar_chunks(
        self, query: str, top_k: int = 5, insurance_company: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """유사한 문서 청크 검색"""
        try:
            # 쿼리 Embedding 생성
            query_embedding = self.embedding_service.get_single_embedding(query)

            if not query_embedding:
                return []

            # 필터 설정
            filter_dict = None
            if insurance_company:
                filter_dict = {"insurance_company": insurance_company}

            # Pinecone에서 검색
            results = self.pinecone_service.search_vectors(
                query_vector=query_embedding, top_k=top_k, filter_dict=filter_dict
            )

            # 검색 결과를 메타데이터와 함께 반환
            chunks_with_metadata = []
            for result in results:
                chunk_id = result["id"]
                score = result["score"]

                # Pinecone ID에서 실제 DocumentChunk ID 추출
                # chunk_1293 -> 1293
                try:
                    if isinstance(chunk_id, str) and chunk_id.startswith("chunk_"):
                        actual_chunk_id = int(chunk_id.replace("chunk_", ""))
                    else:
                        actual_chunk_id = int(chunk_id)
                except (ValueError, TypeError):
                    logger.warning(f"잘못된 chunk_id 형식: {chunk_id}")
                    continue

                # DocumentChunk에서 메타데이터 조회
                try:
                    chunk = DocumentChunk.objects.get(id=actual_chunk_id)
                    chunks_with_metadata.append(
                        {
                            "id": chunk_id,
                            "score": score,
                            "metadata": {
                                "content": chunk.chunk_text,
                                "document_id": (
                                    chunk.document.id if chunk.document else None
                                ),
                                "document_title": (
                                    chunk.document.title
                                    if chunk.document
                                    else "알 수 없는 문서"
                                ),
                                "insurance_company": (
                                    chunk.document.insurance_company.name
                                    if chunk.document
                                    and chunk.document.insurance_company
                                    else "알 수 없는 보험사"
                                ),
                                "chunk_index": chunk.chunk_index,
                                "created_at": (
                                    chunk.created_at.isoformat()
                                    if chunk.created_at
                                    else None
                                ),
                            },
                        }
                    )
                except DocumentChunk.DoesNotExist:
                    logger.warning(
                        f"DocumentChunk {actual_chunk_id}를 찾을 수 없습니다."
                    )
                    continue

            logger.info(
                f"'{query}'에 대한 {len(chunks_with_metadata)}개 유사 청크 검색 완료"
            )
            return chunks_with_metadata

        except Exception as e:
            logger.error(f"유사 청크 검색 실패: {e}")
            return []

    def delete_document_vectors(self, document_id: int) -> bool:
        """특정 문서의 모든 벡터 삭제"""
        try:
            # 해당 문서의 모든 벡터 ID 조회
            filter_dict = {"document_id": str(document_id)}
            results = self.pinecone_service.search_vectors(
                query_vector=[0.0] * self.pinecone_service.dimension,  # 더미 벡터
                top_k=1000,  # 충분히 큰 수
                filter_dict=filter_dict,
            )

            if results:
                vector_ids = [result["id"] for result in results]
                return self.pinecone_service.delete_vectors(vector_ids)

            return True

        except Exception as e:
            logger.error(f"문서 벡터 삭제 실패: {e}")
            return False

    def get_index_statistics(self) -> Dict[str, Any]:
        """인덱스 통계 정보 조회"""
        return self.pinecone_service.get_index_stats()


class RAGChatbotService:
    """RAG 챗봇 서비스 (하이브리드 검색 적용)"""

    def __init__(self):
        self.document_service = DocumentEmbeddingService()
        self.embedding_service = EmbeddingService()
        self.openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.openai_model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

        # 하이브리드 검색 서비스 초기화
        self.hybrid_search_service = HybridSearchService(
            self.document_service, self.embedding_service
        )

        # 연락처 정보 서비스 초기화
        self.contact_info_service = ContactInfoService()

        # 캐싱 서비스 초기화
        self.cache_service = CacheService()

        # 보험 추천 서비스 초기화
        self.insurance_service = InsuranceRecommendationService()

        # ML 모델 초기화
        self.premium_predictor = InsurancePremiumPredictor()
        self.behavior_analyzer = CustomerBehaviorAnalyzer()

    def search_relevant_documents(
        self, query: str, top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색을 사용한 관련 문서 청크 검색"""
        try:
            # 하이브리드 검색 수행 (벡터 + 키워드)
            relevant_chunks = self.hybrid_search_service.hybrid_search(query)

            logger.info(
                f"'{query}'에 대한 하이브리드 검색 완료: {len(relevant_chunks)}개 결과"
            )
            return relevant_chunks

        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            # 실패 시 기존 벡터 검색으로 폴백
            try:
                fallback_chunks = self.document_service.search_similar_chunks(
                    query=query, top_k=top_k
                )
                logger.info(f"폴백 검색 결과: {len(fallback_chunks)}개")
                return fallback_chunks
            except Exception as fallback_error:
                logger.error(f"폴백 검색도 실패: {fallback_error}")
                return []

    def generate_response(
        self, user_message: str, relevant_chunks: List[Dict[str, Any]], user=None
    ) -> Dict[str, Any]:
        """OpenAI API를 사용하여 RAG 답변 생성 (캐싱 + 연락처 정보 우선 처리)"""
        try:
            # 1. 캐시에서 응답 확인
            cached_response = self.cache_service.get_cached_response(user_message)
            if cached_response:
                logger.info("캐시된 응답 사용")
                return {
                    "answer": cached_response["response"],
                    "metadata": {
                        **cached_response["metadata"],
                        "cached": True,
                        "cached_at": cached_response["cached_at"],
                    },
                }

            # 2. 보험 추천 관련 질문인지 확인하고 우선 처리
            if self._is_insurance_recommendation_request(user_message):
                logger.info("보험 추천 요청 감지")
                return self._handle_insurance_recommendation(user_message, user)

            # 3. 연락처 관련 질문인지 확인하고 우선 처리
            contact_results = self.contact_info_service.search_contact_info(
                user_message
            )
            if contact_results:
                logger.info(
                    f"연락처 정보 서비스에서 {len(contact_results)}개 결과 발견"
                )
                response = self.contact_info_service.format_contact_response(
                    contact_results
                )

                metadata = {
                    "contact_info_used": True,
                    "contact_results_count": len(contact_results),
                    "model_used": "contact_info_service",
                    "generated_at": timezone.now().isoformat(),
                }

                result = {"answer": response, "metadata": metadata}

                # 연락처 정보 응답 캐시 저장
                self.cache_service.cache_response(user_message, result)

                logger.info(f"연락처 정보 서비스 응답 길이: {len(result['answer'])}")
                return result

            # 3. 일반적인 RAG 처리
            if not self.openai_api_key:
                raise Exception("OpenAI API 키가 설정되지 않았습니다.")

            # 컨텍스트 구성
            context = self._build_context(relevant_chunks)

            # 프롬프트 구성
            prompt = self._build_prompt(user_message, context)

            # OpenAI API 호출
            response = self._call_openai_api(prompt)

            # 응답 로깅
            logger.info(f"OpenAI API 응답 길이: {len(response) if response else 0}")
            logger.info(
                f"OpenAI API 응답 내용 (처음 100자): {response[:100] if response else 'None'}"
            )

            # 메타데이터 구성
            metadata = {
                "relevant_chunks_count": len(relevant_chunks),
                "chunks_used": [chunk.get("metadata", {}) for chunk in relevant_chunks],
                "model_used": self.openai_model,
                "generated_at": timezone.now().isoformat(),
            }

            result = {"answer": response, "metadata": metadata}

            # RAG 응답 캐시 저장
            self.cache_service.cache_response(user_message, result)

            logger.info(
                f"최종 반환 결과 - answer 길이: {len(result['answer']) if result['answer'] else 0}"
            )

            return result

        except Exception as e:
            logger.error(f"RAG 답변 생성 실패: {e}")
            # 오류 시 기본 답변 반환
            return {
                "answer": f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e)},
            }

    def _build_context(self, relevant_chunks: List[Dict[str, Any]]) -> str:
        """하이브리드 검색 결과를 바탕으로 향상된 컨텍스트 구성"""
        if not relevant_chunks:
            return "관련 문서를 찾을 수 없습니다."

        # 하이브리드 검색 서비스의 향상된 컨텍스트 구축 사용
        return self.hybrid_search_service.build_enhanced_context(relevant_chunks)

    def _build_prompt(self, user_message: str, context: str) -> str:
        """향상된 RAG 프롬프트 구성"""
        return f"""당신은 자동차 보험 전문 상담사입니다. 제공된 보험 문서를 참고하여 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.

**중요한 지침:**
1. 문서에 있는 정보를 바탕으로 답변하세요
2. 부분적으로 관련된 정보가 있다면 그것을 바탕으로 답변하고, 추가 정보가 필요하다면 언급하세요
3. 완전히 관련 없는 경우에만 "문서에 해당 정보가 없습니다"라고 답변하세요
4. 질문을 그대로 반복하지 말고 실제 답변을 제공하세요
5. 답변은 명확하고 이해하기 쉽게 작성하세요
6. 필요시 단계별로 설명하세요
7. 신뢰도가 높은 정보를 우선적으로 사용하세요
8. 사용자가 추가 질문을 할 수 있도록 도움이 되는 정보를 제공하세요

**참고 문서:**
{context}

**사용자 질문:** {user_message}

**전문가 답변:**"""

    def _call_openai_api(self, prompt: str) -> str:
        """OpenAI API 호출"""
        try:
            import openai

            client = openai.OpenAI(api_key=self.openai_api_key)

            logger.info(f"OpenAI API 호출 시작 - 모델: {self.openai_model}")
            logger.info(f"프롬프트 길이: {len(prompt)}")

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 자동차 보험 전문 상담사입니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=1000,
            )

            logger.info(f"OpenAI API 응답 객체: {type(response)}")
            logger.info(f"OpenAI API 응답 choices 개수: {len(response.choices)}")

            if response.choices:
                content = response.choices[0].message.content
                logger.info(f"OpenAI API 응답 content 타입: {type(content)}")
                logger.info(
                    f"OpenAI API 응답 content 길이: {len(content) if content else 0}"
                )
                logger.info(
                    f"OpenAI API 응답 content (처음 200자): {content[:200] if content else 'None'}"
                )

                return content.strip() if content else ""
            else:
                logger.error("OpenAI API 응답에 choices가 없습니다")
                return ""

        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            raise Exception(f"OpenAI API 오류: {str(e)}")

    def get_chat_suggestions(self) -> List[str]:
        """자주 묻는 질문 제안"""
        return [
            "자동차보험 가입 시 필요한 서류는 무엇인가요?",
            "보험료 할인 혜택은 어떻게 받을 수 있나요?",
            "사고 발생 시 보험금 청구 절차는 어떻게 되나요?",
            "보험 계약 해지 시 환급금은 언제 받을 수 있나요?",
            "보험사별 특별 할인 혜택이 있나요?",
            "자동차보험 보장 범위는 어떻게 되나요?",
            "무사고 할인은 어떻게 적용되나요?",
            "보험료 계산 방법을 알려주세요.",
            "자동차보험 추천해주세요",
            "나에게 맞는 보험을 찾아주세요",
        ]

    def _is_insurance_recommendation_request(self, user_message: str) -> bool:
        """보험 추천 요청인지 확인"""
        recommendation_keywords = [
            "보험 추천",
            "보험 추천해",
            "보험 추천해주",
            "보험 추천해주세요",
            "맞는 보험",
            "적합한 보험",
            "좋은 보험",
            "괜찮은 보험",
            "보험 찾아",
            "보험 찾아주",
            "보험 찾아주세요",
            "보험 상품",
            "보험 상품 추천",
            "보험 상품 추천해",
            "자동차보험 추천",
            "자동차보험 추천해",
            "자동차보험 추천해주세요",
            "나에게 맞는",
            "나에게 적합한",
            "나에게 좋은",
            "보험료 계산",
            "보험료 계산해",
            "보험료 계산해주세요",
            "견적",
            "견적 받고 싶어",
            "견적 받고 싶어요",
        ]

        user_message_lower = user_message.lower()
        return any(keyword in user_message_lower for keyword in recommendation_keywords)

    def _handle_insurance_recommendation(
        self, user_message: str, user=None
    ) -> Dict[str, Any]:
        """보험 추천 요청 처리"""
        try:
            # 사용자 정보 확인

            if user is None:
                return {
                    "answer": "보험 추천을 받으시려면 로그인이 필요합니다. 먼저 로그인해주세요.",
                    "metadata": {
                        "insurance_recommendation_requested": True,
                        "login_required": True,
                        "model_used": "insurance_service",
                        "generated_at": timezone.now().isoformat(),
                    },
                }

            # 사용자 프로필 확인
            try:
                profile = user.profile
                has_complete_profile = (
                    profile.birth_date
                    and profile.gender
                    and profile.residence_area
                    and profile.driving_experience is not None
                    and profile.car_type
                    and profile.annual_mileage is not None
                    and profile.accident_history is not None
                    and profile.coverage_level
                )
            except:
                has_complete_profile = False

            # 프로필이 불완전한 경우 말풍선 UI 제공
            if not has_complete_profile:
                return {
                    "answer": self._get_profile_input_message(),
                    "metadata": {
                        "insurance_recommendation_requested": True,
                        "profile_incomplete": True,
                        "show_profile_input": True,
                        "model_used": "insurance_service",
                        "generated_at": timezone.now().isoformat(),
                    },
                }

                # ML 기반 보험료 예측 (안전장치 포함)
            try:
                ml_prediction = self._get_ml_premium_prediction(profile)
                if "error" in ml_prediction:
                    logger.warning(
                        f"ML 예측 실패, 기본값 사용: {ml_prediction['error']}"
                    )
                    ml_prediction = {
                        "predicted_premium": 500000,
                        "confidence_score": 0.5,
                        "prediction_timestamp": timezone.now().isoformat(),
                        "model_version": "1.0",
                    }
            except Exception as e:
                logger.error(f"ML 예측 중 예외 발생: {e}")
                ml_prediction = {
                    "predicted_premium": 500000,
                    "confidence_score": 0.5,
                    "prediction_timestamp": timezone.now().isoformat(),
                    "model_version": "1.0",
                }

            # 보험 추천 계산
            result = self.insurance_service.calculate_insurance_recommendations(
                user, "chatbot"
            )

            # 사용자 행동 분석 (안전장치 포함)
            try:
                user_preferences = self._analyze_user_preferences(user)
                if "error" in user_preferences:
                    logger.warning(
                        f"사용자 선호도 분석 실패, 기본값 사용: {user_preferences['error']}"
                    )
                    user_preferences = {"preferences": {}, "confidence": 0.0}
            except Exception as e:
                logger.error(f"사용자 선호도 분석 중 예외 발생: {e}")
                user_preferences = {"preferences": {}, "confidence": 0.0}

            # 추천 결과를 사용자 친화적인 형태로 포맷팅 (ML 정보 포함)
            formatted_response = self._format_insurance_recommendation_with_ml(
                result, ml_prediction, user_preferences
            )

            metadata = {
                "insurance_recommendation_requested": True,
                "session_id": result.get("session_id"),
                "recommendation_id": result.get("recommendation_id"),
                "quotes_count": len(result.get("quotes", [])),
                "ml_prediction": ml_prediction,
                "user_preferences": user_preferences,
                "model_used": "insurance_service_with_ml",
                "generated_at": timezone.now().isoformat(),
            }

            return {"answer": formatted_response, "metadata": metadata}

        except Exception as e:
            logger.error(f"보험 추천 처리 실패: {e}")
            return {
                "answer": f"보험 추천 처리 중 오류가 발생했습니다: {str(e)}",
                "metadata": {
                    "insurance_recommendation_requested": True,
                    "error": str(e),
                    "model_used": "insurance_service",
                    "generated_at": timezone.now().isoformat(),
                },
            }

    def _get_ml_premium_prediction(self, profile) -> Dict[str, Any]:
        """ML 기반 보험료 예측"""
        try:
            if not profile:
                logger.warning("프로필 정보가 없습니다.")
                return {"error": "프로필 정보가 없습니다."}

            # 사용자 프로필 데이터 준비
            user_profile = {
                "age": profile.get_age() or 30,
                "gender": profile.gender or "M",
                "driving_experience": profile.driving_experience or 5,
                "annual_mileage": profile.annual_mileage or 12000,
                "accident_history": profile.accident_history or 0,
                "residence_area": profile.residence_area or "서울",
                "car_type": profile.car_type or "준중형",
                "coverage_level": profile.coverage_level or "표준",
            }

            logger.info(f"ML 예측 시작: {user_profile}")

            # ML 모델로 예측
            prediction = self.premium_predictor.predict_premium(user_profile)

            logger.info(f"ML 예측 완료: {prediction}")

            return prediction

        except Exception as e:
            logger.error(f"ML 예측 중 오류: {e}", exc_info=True)
            return {"error": f"예측 중 오류가 발생했습니다: {str(e)}"}

    def _analyze_user_preferences(self, user) -> Dict[str, Any]:
        """사용자 선호도 분석"""
        try:
            if not user:
                return {"error": "사용자 정보가 없습니다."}

            # 사용자 행동 분석
            preferences = self.behavior_analyzer.analyze_user_preferences(user.id)

            return preferences

        except Exception as e:
            logger.error(f"사용자 선호도 분석 중 오류: {e}")
            return {"error": f"분석 중 오류가 발생했습니다: {str(e)}"}

    def _format_insurance_recommendation(self, result: Dict[str, Any]) -> str:
        """보험 추천 결과를 사용자 친화적인 형태로 포맷팅"""
        quotes = result.get("quotes", [])
        if not quotes:
            return "죄송합니다. 적절한 보험 상품을 찾을 수 없습니다."

        # 상위 3개 보험사 추천
        top_quotes = quotes[:3]

        response_parts = []
        response_parts.append("🔍 **자동차보험 추천 결과**")
        response_parts.append("")

        for i, quote in enumerate(top_quotes, 1):
            company = quote["company"]
            annual_premium = quote["annual_premium"]
            monthly_premium = quote["monthly_premium"]
            coverage_level = quote["coverage_level"]
            customer_satisfaction = quote["customer_satisfaction"]

            response_parts.append(f"**{i}. {company}**")
            response_parts.append(f"   💰 연간 보험료: {annual_premium:,}원")
            response_parts.append(f"   📅 월 납입액: {monthly_premium:,}원")
            response_parts.append(f"   🛡️ 보장 수준: {coverage_level}")
            response_parts.append(f"   ⭐ 고객 만족도: {customer_satisfaction}/5.0")

            if quote.get("special_discount"):
                response_parts.append(f"   🎁 특별 할인: {quote['special_discount']}")

            response_parts.append("")

        # 시장 분석 정보
        market_analysis = result.get("market_analysis", {})
        if market_analysis:
            response_parts.append("📊 **시장 분석**")
            response_parts.append(
                f"   • 최저가: {market_analysis.get('lowest_premium', 0):,}원"
            )
            response_parts.append(
                f"   • 평균가: {market_analysis.get('average_premium', 0):,}원"
            )
            response_parts.append(
                f"   • 가성비 최고: {market_analysis.get('best_value', 'N/A')}"
            )
            response_parts.append("")

        # 사용자 정보
        user_info = result.get("user_info", {})
        if user_info:
            response_parts.append("👤 **사용자 정보**")
            response_parts.append(f"   • 위험도: {user_info.get('risk_level', 'N/A')}")
            response_parts.append(
                f"   • 추천 보장: {user_info.get('recommended_coverage', 'N/A')}"
            )
            response_parts.append("")

        response_parts.append("💡 **추천 이유**")
        response_parts.append(result.get("recommendation_reason", "개인 맞춤형 추천"))
        response_parts.append("")
        response_parts.append(
            "더 자세한 정보나 다른 보험사 견적이 필요하시면 말씀해주세요!"
        )

        return "\n".join(response_parts)

    def _format_insurance_recommendation_with_ml(
        self,
        result: Dict[str, Any],
        ml_prediction: Dict[str, Any],
        user_preferences: Dict[str, Any],
    ) -> str:
        """ML 정보를 포함한 보험 추천 결과 포맷팅"""
        quotes = result.get("quotes", [])
        if not quotes:
            return "죄송합니다. 적절한 보험 상품을 찾을 수 없습니다."

        # 상위 3개 보험사 추천
        top_quotes = quotes[:3]

        response_parts = []
        response_parts.append("🔍 **자동차보험 추천 결과 (AI 분석 포함)**")
        response_parts.append("")

        # ML 예측 정보 추가
        if "predicted_premium" in ml_prediction:
            predicted_premium = ml_prediction["predicted_premium"]
            confidence_score = ml_prediction.get("confidence_score", 0)
            confidence_percent = int(confidence_score * 100)

            response_parts.append("🤖 **AI 예측 보험료**")
            response_parts.append(f"   💰 예상 보험료: {predicted_premium:,}원")
            response_parts.append(f"   📊 예측 신뢰도: {confidence_percent}%")
            response_parts.append("")

        # 사용자 선호도 정보 추가
        if "preferences" in user_preferences and user_preferences["preferences"]:
            prefs = user_preferences["preferences"]
            response_parts.append("👤 **개인화 분석**")

            if "price_sensitivity" in prefs:
                response_parts.append(
                    f"   💡 가격 민감도: {prefs['price_sensitivity']}"
                )
            if "preferred_coverage_level" in prefs:
                response_parts.append(
                    f"   🛡️ 선호 보장 수준: {prefs['preferred_coverage_level']}"
                )
            if "preferred_car_type" in prefs:
                response_parts.append(f"   🚗 선호 차종: {prefs['preferred_car_type']}")

            response_parts.append("")

        # 기존 추천 결과
        response_parts.append("🏆 **추천 보험사**")
        response_parts.append("")

        for i, quote in enumerate(top_quotes, 1):
            company = quote["company"]
            annual_premium = quote["annual_premium"]
            monthly_premium = quote["monthly_premium"]
            coverage_level = quote["coverage_level"]
            customer_satisfaction = quote["customer_satisfaction"]

            response_parts.append(f"**{i}. {company}**")
            response_parts.append(f"   💰 연간 보험료: {annual_premium:,}원")
            response_parts.append(f"   📅 월 납입액: {monthly_premium:,}원")
            response_parts.append(f"   🛡️ 보장 수준: {coverage_level}")
            response_parts.append(f"   ⭐ 고객 만족도: {customer_satisfaction}/5.0")

            if quote.get("special_discount"):
                response_parts.append(f"   🎁 특별 할인: {quote['special_discount']}")
            response_parts.append("")

        # 시장 분석 정보
        market_analysis = result.get("market_analysis", {})
        if market_analysis:
            response_parts.append("📊 **시장 분석**")
            if market_analysis.get("lowest_premium"):
                response_parts.append(
                    f"   • 최저가: {market_analysis['lowest_premium']:,}원"
                )
            if market_analysis.get("average_premium"):
                response_parts.append(
                    f"   • 평균가: {market_analysis['average_premium']:,}원"
                )
            if market_analysis.get("best_value"):
                response_parts.append(
                    f"   • 가성비 최고: {market_analysis['best_value']}"
                )
            response_parts.append("")

        # 사용자 정보
        user_info = result.get("user_info", {})
        if user_info:
            response_parts.append("👤 **사용자 정보**")
            if user_info.get("risk_level"):
                response_parts.append(f"   • 위험도: {user_info['risk_level']}")
            if user_info.get("recommended_coverage"):
                response_parts.append(
                    f"   • 추천 보장: {user_info['recommended_coverage']}"
                )
            response_parts.append("")

        # 추천 이유
        if result.get("recommendation_reason"):
            response_parts.append("💡 **추천 이유**")
            response_parts.append(result["recommendation_reason"])
            response_parts.append("")

        response_parts.append(
            "더 자세한 정보나 다른 보험사 견적이 필요하시면 말씀해주세요!"
        )

        return "\n".join(response_parts)

    def _get_profile_input_message(self) -> str:
        """프로필 입력을 위한 말풍선 메시지 생성"""
        return """🔍 **자동차보험 맞춤 추천을 위해 몇 가지 정보가 필요합니다**

정확한 보험 추천을 받으시려면 아래 정보를 입력해주세요:

**📋 필요한 정보:**
• 생년월일
• 성별
• 거주 지역
• 운전 경력 (년)
• 차종
• 연간 주행거리 (km)
• 사고 경력 (횟수)
• 원하는 보장 수준

**💡 말풍선을 클릭하여 정보를 입력해주세요!**

입력하신 정보는 안전하게 저장되며, 더 정확한 보험 추천을 위해 사용됩니다."""
