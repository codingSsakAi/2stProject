"""
RAG (Retrieval-Augmented Generation) 서비스
보험 약관 문서의 벡터화, 검색, 생성 기능을 제공합니다.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import hashlib

import pinecone
import openai
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import PolicyDocument, InsuranceCompany

# 로깅 설정
logger = logging.getLogger(__name__)


class RAGService:
    """통합 RAG 서비스 클래스"""
    
    def __init__(self):
        """RAG 서비스 초기화"""
        self.index_name = settings.PINECONE_INDEX_NAME
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.embedding_dimension = settings.EMBEDDING_DIMENSION
        
        # Pinecone 초기화
        self._initialize_pinecone()
        
        # OpenAI 초기화
        self._initialize_openai()
    
    def _initialize_pinecone(self):
        """Pinecone 초기화"""
        try:
            if not settings.PINECONE_API_KEY:
                logger.warning("Pinecone API 키가 설정되지 않았습니다.")
                return
            
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            
            # 인덱스가 존재하지 않으면 생성
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric='cosine'
                )
                logger.info(f"Pinecone 인덱스 '{self.index_name}' 생성됨")
            
            self.pinecone_index = pinecone.Index(self.index_name)
            logger.info("Pinecone 초기화 완료")
            
        except Exception as e:
            logger.error(f"Pinecone 초기화 실패: {e}")
            self.pinecone_index = None
    
    def _initialize_openai(self):
        """OpenAI 초기화"""
        try:
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API 키가 설정되지 않았습니다.")
                return
            
            openai.api_key = settings.OPENAI_API_KEY
            logger.info("OpenAI 초기화 완료")
            
        except Exception as e:
            logger.error(f"OpenAI 초기화 실패: {e}")
    
    def chunk_text(self, text: str) -> List[str]:
        """텍스트를 청크로 분할"""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 청크 끝에서 문장 경계 찾기
            if end < len(text):
                # 마침표, 느낌표, 물음표로 문장 경계 찾기
                sentence_end = text.rfind('.', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('!', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('?', start, end)
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 오버랩을 고려한 다음 시작점
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트의 임베딩 벡터 생성"""
        try:
            if not openai.api_key:
                logger.error("OpenAI API 키가 설정되지 않았습니다.")
                return []
            
            response = openai.Embedding.create(
                input=text,
                model="text-embedding-ada-002"
            )
            
            return response['data'][0]['embedding']
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return []
    
    def upload_document(self, document: PolicyDocument) -> bool:
        """문서를 Pinecone에 업로드"""
        try:
            if not self.pinecone_index:
                logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
                return False
            
            # 문서 텍스트 읽기
            text = self._read_document_text(document)
            if not text:
                logger.error(f"문서 텍스트를 읽을 수 없습니다: {document.id}")
                return False
            
            # 텍스트 청킹
            chunks = self.chunk_text(text)
            if not chunks:
                logger.warning(f"문서에서 청크를 생성할 수 없습니다: {document.id}")
                return False
            
            # 벡터 생성 및 업로드
            vectors = []
            for i, chunk in enumerate(chunks):
                # 임베딩 생성
                embedding = self.get_embedding(chunk)
                if not embedding:
                    continue
                
                # 벡터 ID 생성 (고유성 보장)
                vector_id = f"{document.company.code}_{document.version}_{i}_{hashlib.md5(chunk.encode()).hexdigest()[:8]}"
                
                # 메타데이터
                metadata = {
                    'company_code': document.company.code,
                    'company_name': document.company.name,
                    'document_type': document.document_type,
                    'version': document.version,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'text': chunk[:500],  # 검색용 텍스트 미리보기
                    'document_id': str(document.id),
                    'upload_date': document.upload_date.isoformat() if document.upload_date else None
                }
                
                vectors.append((vector_id, embedding, metadata))
            
            # Pinecone에 업로드
            if vectors:
                self.pinecone_index.upsert(vectors=vectors)
                logger.info(f"문서 업로드 완료: {document.id}, {len(vectors)}개 벡터")
                
                # 문서 상태 업데이트
                document.pinecone_index_id = self.index_name
                document.save(update_fields=['pinecone_index_id'])
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"문서 업로드 실패: {e}")
            return False
    
    def _read_document_text(self, document: PolicyDocument) -> str:
        """문서 텍스트 읽기"""
        try:
            if document.document_path:
                file_path = Path(settings.MEDIA_ROOT) / document.document_path
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            
            # DOCX 파일이 없는 경우 PDF에서 텍스트 추출 시도
            if hasattr(document, 'pdf_path') and document.pdf_path:
                return self._extract_pdf_text(document.pdf_path)
            
            return ""
            
        except Exception as e:
            logger.error(f"문서 텍스트 읽기 실패: {e}")
            return ""
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        try:
            import fitz  # PyMuPDF
            
            file_path = Path(settings.MEDIA_ROOT) / pdf_path
            if not file_path.exists():
                return ""
            
            doc = fitz.open(str(file_path))
            text = ""
            
            for page in doc:
                text += page.get_text()
            
            doc.close()
            return text
            
        except Exception as e:
            logger.error(f"PDF 텍스트 추출 실패: {e}")
            return ""
    
    def search_documents(self, query: str, company_filter: str = None, 
                        top_k: int = 10) -> List[Dict[str, Any]]:
        """문서 검색"""
        try:
            if not self.pinecone_index:
                logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
                return []
            
            # 쿼리 임베딩 생성
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # 필터 설정
            filter_dict = {}
            if company_filter:
                filter_dict['company_code'] = company_filter
            
            # Pinecone 검색
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
            
            # 결과 정리
            search_results = []
            for match in results.matches:
                search_results.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata,
                    'text': match.metadata.get('text', ''),
                    'company_name': match.metadata.get('company_name', ''),
                    'document_type': match.metadata.get('document_type', ''),
                    'version': match.metadata.get('version', '')
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
    
    def generate_response(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """RAG 기반 응답 생성"""
        try:
            if not openai.api_key:
                return "OpenAI API 키가 설정되지 않았습니다."
            
            # 컨텍스트 구성
            context_text = ""
            for doc in context_docs:
                context_text += f"문서: {doc['metadata'].get('company_name', '')}\n"
                context_text += f"내용: {doc['metadata'].get('text', '')}\n\n"
            
            # 프롬프트 구성
            prompt = f"""
당신은 자동차 보험 전문 상담사입니다. 다음 정보를 바탕으로 사용자의 질문에 답변해주세요.

참고 문서:
{context_text}

사용자 질문: {query}

답변은 다음 형식으로 작성해주세요:
1. 질문에 대한 명확한 답변
2. 관련 보험 약관 정보
3. 추가 고려사항이나 주의사항

답변:
"""
            
            # OpenAI API 호출
            response = openai.ChatCompletion.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 자동차 보험 전문 상담사입니다. 정확하고 도움이 되는 답변을 제공하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"응답 생성 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    def delete_document(self, document: PolicyDocument) -> bool:
        """문서 삭제"""
        try:
            if not self.pinecone_index:
                return False
            
            # 해당 문서의 모든 벡터 삭제
            filter_dict = {'document_id': str(document.id)}
            
            # 삭제할 벡터 ID 찾기
            results = self.pinecone_index.query(
                vector=[0] * self.embedding_dimension,  # 더미 벡터
                top_k=1000,
                include_metadata=True,
                filter=filter_dict
            )
            
            # 벡터 삭제
            if results.matches:
                vector_ids = [match.id for match in results.matches]
                self.pinecone_index.delete(ids=vector_ids)
                logger.info(f"문서 삭제 완료: {document.id}, {len(vector_ids)}개 벡터")
            
            # 문서 상태 업데이트
            document.pinecone_index_id = ""
            document.save(update_fields=['pinecone_index_id'])
            
            return True
            
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        try:
            if not self.pinecone_index:
                return {}
            
            stats = self.pinecone_index.describe_index_stats()
            
            # 보험사별 문서 수 계산
            company_stats = {}
            if 'namespaces' in stats:
                for namespace, data in stats['namespaces'].items():
                    company_stats[namespace] = data['vector_count']
            
            return {
                'total_vectors': stats.get('total_vector_count', 0),
                'dimension': stats.get('dimension', 0),
                'company_stats': company_stats,
                'index_name': self.index_name
            }
            
        except Exception as e:
            logger.error(f"인덱스 통계 조회 실패: {e}")
            return {}


# 싱글톤 인스턴스
rag_service = RAGService() 