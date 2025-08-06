import PyPDF2
from sentence_transformers import SentenceTransformer
import uuid
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from .pinecone_client import get_index


# 384차원 임베딩 모델
model = SentenceTransformer('all-MiniLM-L6-v2')

class EnhancedPDFProcessor:
    def __init__(self):
        self.index = get_index()
        self.documents_path = Path(__file__).parent / 'documents'
        self.insurance_companies = [
            '삼성화재', '현대해상', '메리츠화재', 'DB손해보험',
            '롯데손해보험', '하나손해보험', '흥국화재', 'MG손해보험', '캐롯손해보험'
        ]
        
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """PDF에서 텍스트 추출 (한글 처리 개선)"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        # 페이지 번호 추가
                        text += f"\n\n=== 페이지 {page_num + 1} ===\n"
                        text += page_text
                        
        except Exception as e:
            print(f"PDF 읽기 오류 ({pdf_path}): {e}")
            return None
        return text
    
    def smart_chunk_text(self, text: str, company_name: str, document_type: str) -> List[Dict]:
        """보험 약관에 특화된 스마트 청킹"""
        if not text:
            return []
        
        chunks = []
        
        # 조문별로 분할 (제X조, 제X장 등)
        article_pattern = r'(제\s*\d+\s*[조장절].*?)(?=제\s*\d+\s*[조장절]|$)'
        articles = re.findall(article_pattern, text, re.DOTALL)
        
        if not articles:
            # 조문이 없는 경우 일반적인 청킹
            return self.general_chunk_text(text, company_name, document_type)
        
        for i, article in enumerate(articles):
            article = article.strip()
            if len(article) < 50:  # 너무 짧은 조문은 스킵
                continue
                
            # 조문 제목 추출
            title_match = re.match(r'(제\s*\d+\s*[조장절][^:\n]*)', article)
            article_title = title_match.group(1) if title_match else f"조문 {i+1}"
            
            # 긴 조문은 소절로 나누기
            if len(article) > 1000:
                sub_chunks = self.split_long_article(article, article_title)
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    'text': article,
                    'title': article_title,
                    'company': company_name,
                    'document_type': document_type,
                    'chunk_type': 'article',
                    'length': len(article)
                })
        
        return chunks
    
    def split_long_article(self, article: str, article_title: str) -> List[Dict]:
        """긴 조문을 소절로 분할"""
        chunks = []
        
        # 항목별로 분할 (1., 2., 가., 나. 등)
        item_pattern = r'([1-9]\.|[가-힣]\.|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩)'
        parts = re.split(item_pattern, article)
        
        current_chunk = parts[0]  # 조문 제목 부분
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                item_marker = parts[i]
                item_content = parts[i + 1]
                
                # 청크가 너무 길어지면 분할
                if len(current_chunk) > 800:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'title': article_title,
                        'company': '',
                        'document_type': '',
                        'chunk_type': 'article_part',
                        'length': len(current_chunk)
                    })
                    current_chunk = f"{article_title}\n{item_marker}{item_content}"
                else:
                    current_chunk += f"{item_marker}{item_content}"
        
        # 마지막 청크 추가
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'title': article_title,
                'company': '',
                'document_type': '',
                'chunk_type': 'article_part',
                'length': len(current_chunk)
            })
        
        return chunks
    
    def general_chunk_text(self, text: str, company_name: str, document_type: str) -> List[Dict]:
        """일반적인 텍스트 청킹"""
        chunks = []
        sentences = re.split(r'[.!?]\s+', text)
        
        current_chunk = ""
        chunk_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 청크 크기 체크
            if len(current_chunk) + len(sentence) > 800 and current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'title': f"내용 {len(chunks) + 1}",
                    'company': company_name,
                    'document_type': document_type,
                    'chunk_type': 'general',
                    'length': len(current_chunk)
                })
                current_chunk = sentence
                chunk_sentences = [sentence]
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                chunk_sentences.append(sentence)
        
        # 마지막 청크
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'title': f"내용 {len(chunks) + 1}",
                'company': company_name,
                'document_type': document_type,
                'chunk_type': 'general',
                'length': len(current_chunk)
            })
        
        return chunks
    
    def embed_text(self, text: str) -> List[float]:
        """텍스트를 벡터로 임베딩"""
        try:
            embedding = model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"임베딩 오류: {e}")
            return None
    
    def upload_chunks_to_pinecone(self, chunks: List[Dict], namespace: str = "insurance") -> bool:
        """청크들을 Pinecone에 업로드"""
        if not chunks:
            return False
            
        vectors = []
        successful_chunks = 0
        
        for chunk in chunks:
            embedding = self.embed_text(chunk['text'])
            if embedding:
                vector_id = f"{chunk['company']}_{chunk['document_type']}_{str(uuid.uuid4())[:8]}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "text": chunk['text'][:1000],  # Pinecone 메타데이터 크기 제한
                        "full_text": chunk['text'],  # 전체 텍스트 저장
                        "title": chunk['title'],
                        "company": chunk['company'],
                        "document_type": chunk['document_type'],
                        "chunk_type": chunk['chunk_type'],
                        "length": chunk['length']
                    }
                })
                successful_chunks += 1
        
        if vectors:
            try:
                # 배치 크기로 나누어 업로드 (Pinecone 제한 고려)
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    self.index.upsert(vectors=batch, namespace=namespace)
                    print(f"배치 {i//batch_size + 1} 업로드 완료: {len(batch)}개 벡터")
                
                print(f"✅ {successful_chunks}개 청크가 Pinecone에 업로드됨")
                return True
            except Exception as e:
                print(f"Pinecone 업로드 오류: {e}")
                return False
        return False
    
    def process_company_documents(self, company_name: str) -> bool:
        """특정 보험사의 모든 문서 처리"""
        company_path = self.documents_path / company_name
        
        if not company_path.exists():
            print(f"❌ {company_name} 폴더를 찾을 수 없습니다: {company_path}")
            return False
        
        pdf_files = list(company_path.glob("*.pdf"))
        if not pdf_files:
            print(f"❌ {company_name} 폴더에 PDF 파일이 없습니다")
            return False
        
        print(f"📂 {company_name} 처리 시작: {len(pdf_files)}개 PDF 파일")
        
        total_chunks = 0
        processed_files = 0
        
        for pdf_file in pdf_files:
            print(f"  📄 처리 중: {pdf_file.name}")
            
            # 문서 타입 결정
            document_type = self.determine_document_type(pdf_file.name)
            
            # PDF 텍스트 추출
            text = self.extract_text_from_pdf(pdf_file)
            if not text:
                print(f"    ❌ 텍스트 추출 실패: {pdf_file.name}")
                continue
            
            print(f"    📝 추출된 텍스트 길이: {len(text):,} 문자")
            
            # 스마트 청킹
            chunks = self.smart_chunk_text(text, company_name, document_type)
            print(f"    🔪 생성된 청크 수: {len(chunks)}")
            
            # 각 청크에 회사명과 문서타입 설정
            for chunk in chunks:
                chunk['company'] = company_name
                chunk['document_type'] = document_type
            
            # Pinecone에 업로드
            if self.upload_chunks_to_pinecone(chunks, namespace=f"insurance_{company_name.replace(' ', '_')}"):
                total_chunks += len(chunks)
                processed_files += 1
                print(f"    ✅ {pdf_file.name} 처리 완료")
            else:
                print(f"    ❌ {pdf_file.name} 업로드 실패")
        
        print(f"🎉 {company_name} 처리 완료: {processed_files}/{len(pdf_files)} 파일, 총 {total_chunks} 청크")
        return processed_files > 0
    
    def determine_document_type(self, filename: str) -> str:
        """파일명으로 문서 타입 결정"""
        filename_lower = filename.lower()
        
        if '약관' in filename_lower:
            if '특약' in filename_lower:
                return '특약약관'
            elif '자동차' in filename_lower:
                return '자동차보험약관'
            else:
                return '보험약관'
        elif '상품설명서' in filename_lower:
            return '상품설명서'
        elif '안내서' in filename_lower:
            return '안내서'
        else:
            return '기타문서'
    
    def process_all_companies(self) -> Dict[str, bool]:
        """모든 보험사 문서 처리"""
        results = {}
        
        print("🚀 모든 보험사 문서 처리를 시작합니다...")
        
        for company in self.insurance_companies:
            print(f"\n{'='*50}")
            print(f"처리 대상: {company}")
            print(f"{'='*50}")
            
            result = self.process_company_documents(company)
            results[company] = result
            
            if result:
                print(f"✅ {company} 처리 성공")
            else:
                print(f"❌ {company} 처리 실패")
        
        # 결과 요약
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"\n{'='*50}")
        print(f"📊 전체 처리 결과: {successful}/{total} 보험사 성공")
        print(f"{'='*50}")
        
        for company, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            print(f"{company}: {status}")
        
        return results
    
    def search_company_clauses(self, query: str, company_name: str = None, top_k: int = 5) -> List[Dict]:
        """특정 보험사나 전체에서 약관 검색"""
        query_embedding = self.embed_text(query)
        if not query_embedding:
            return []
        
        try:
            # 네임스페이스 결정
            if company_name:
                namespace = f"insurance_{company_name.replace(' ', '_')}"
            else:
                namespace = "insurance"
            
            # Pinecone에서 검색
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter={"company": company_name} if company_name else None
            )
            
            # 결과 정리
            similar_clauses = []
            for match in results.get('matches', []):
                metadata = match.get('metadata', {})
                similar_clauses.append({
                    'text': metadata.get('full_text', metadata.get('text', '')),
                    'title': metadata.get('title', ''),
                    'company': metadata.get('company', ''),
                    'document_type': metadata.get('document_type', ''),
                    'chunk_type': metadata.get('chunk_type', ''),
                    'score': match.get('score', 0),
                    'length': metadata.get('length', 0)
                })
            
            return similar_clauses
        
        except Exception as e:
            print(f"검색 오류: {e}")
            return []
    
    def get_company_statistics(self) -> Dict[str, Any]:
        """각 보험사별 문서 통계"""
        stats = {}
        
        for company in self.insurance_companies:
            try:
                namespace = f"insurance_{company.replace(' ', '_')}"
                index_stats = self.index.describe_index_stats()
                
                company_stats = index_stats.get('namespaces', {}).get(namespace, {})
                vector_count = company_stats.get('vector_count', 0)
                
                stats[company] = {
                    'vector_count': vector_count,
                    'has_documents': vector_count > 0
                }
            except Exception as e:
                stats[company] = {
                    'vector_count': 0,
                    'has_documents': False,
                    'error': str(e)
                }
        
        return stats

# 기존 함수들과의 호환성을 위한 래퍼 함수들
def search_similar_clauses(query: str, company_name: str = None, top_k: int = 5) -> List[Dict]:
    """기존 코드와의 호환성을 위한 함수"""
    processor = EnhancedPDFProcessor()
    return processor.search_company_clauses(query, company_name, top_k)

def process_pdf_to_pinecone(pdf_path: str, company_name: str, document_type: str = None):
    """단일 PDF 처리 함수"""
    processor = EnhancedPDFProcessor()
    
    if not document_type:
        document_type = processor.determine_document_type(Path(pdf_path).name)
    
    text = processor.extract_text_from_pdf(Path(pdf_path))
    if not text:
        return False
    
    chunks = processor.smart_chunk_text(text, company_name, document_type)
    
    for chunk in chunks:
        chunk['company'] = company_name
        chunk['document_type'] = document_type
    
    return processor.upload_chunks_to_pinecone(chunks)

# Django Management Command로 사용할 수 있는 함수
def initialize_insurance_documents():
    """모든 보험사 문서를 초기화하는 함수"""
    processor = EnhancedPDFProcessor()
    return processor.process_all_companies()