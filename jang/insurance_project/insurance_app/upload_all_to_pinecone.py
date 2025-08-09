import os
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm
import hashlib
import unicodedata
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

import dotenv
dotenv.load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# 환경변수로 인덱스 이름 관리
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses-new")
DOC_ROOT = os.path.join(os.path.dirname(__file__), "documents")

# 1. 임베딩 모델 준비
EMBED_MODEL = "jhgan/ko-sroberta-multitask"
model = SentenceTransformer(EMBED_MODEL)

# 2. Pinecone 최신 방식 초기화
pc = Pinecone(api_key=PINECONE_API_KEY)

# 인덱스 존재 확인 및 생성
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    pc.create_index(
        name=INDEX_NAME,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )
index = pc.Index(INDEX_NAME)

# # 1. 인덱스 초기화
# index.delete(deleteAll=True)
# print(f"인덱스 [{INDEX_NAME}]의 모든 벡터 데이터가 삭제되었습니다.")


def sanitize_for_ascii_id(text):
    """
    한글 및 특수문자를 ASCII 안전한 형태로 변환
    """
    # 1. 유니코드 정규화 (NFD: 분해형태)
    text = unicodedata.normalize('NFD', text)
    
    # 2. ASCII가 아닌 문자들을 제거하고 안전한 문자로 대체
    # 한글, 특수문자 등을 언더스코어로 대체
    ascii_text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    
    # 3. 연속된 언더스코어를 하나로 축약
    ascii_text = re.sub(r'_+', '_', ascii_text)
    
    # 4. 앞뒤 언더스코어 제거
    ascii_text = ascii_text.strip('_')
    
    # 5. 빈 문자열인 경우 기본값 설정
    if not ascii_text:
        ascii_text = "unknown"
    
    return ascii_text

def create_safe_vector_id(company, doc_name, page_num, chunk_idx):
    """
    ASCII 안전한 벡터 ID 생성
    """
    # 회사명과 문서명을 ASCII 안전하게 변환
    safe_company = sanitize_for_ascii_id(company)
    safe_doc_name = sanitize_for_ascii_id(doc_name)
    
    # 기본 ID 생성
    base_id = f"{safe_company}_{safe_doc_name}_{page_num}_{chunk_idx}"
    
    # ID가 너무 길면 해시로 축약 (Pinecone ID 길이 제한 고려)
    if len(base_id) > 100:
        # 원본 정보의 해시값 생성
        hash_part = hashlib.md5(f"{company}_{doc_name}".encode('utf-8')).hexdigest()[:8]
        base_id = f"{safe_company[:20]}_{hash_part}_{page_num}_{chunk_idx}"
    
    return base_id

def chunk_text(text, max_length=500, overlap=50):
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + max_length, text_length)
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += max_length - overlap
    return chunks

def process_pdf(company, pdf_path):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    vectors = []

    # PDF 이미지 페이지 변환 (전체 미리 변환)
    images = convert_from_path(pdf_path, dpi=200)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            # OCR: 이미지 → 텍스트
            ocr_text = ""
            try:
                img = images[page_num - 1]
                ocr_text = pytesseract.image_to_string(img, lang="kor+eng")
            except Exception:
                ocr_text = ""
            if ocr_text.strip():
                text += "\n" + ocr_text.strip()
            if not text or len(text.strip()) < 50:
                continue
            page_chunks = chunk_text(text)
            for idx, chunk in enumerate(page_chunks):
                meta = {
                    "company": company,  # 원본 한글명은 메타데이터에 보존
                    "file": doc_name,    # 원본 파일명도 메타데이터에 보존
                    "page": page_num,
                    "chunk_idx": idx,
                    "text": chunk  # metadata에 텍스트도 저장
                }
                # ASCII 안전한 벡터 ID 생성
                vec_id = create_safe_vector_id(company, doc_name, page_num, idx)
                vectors.append((vec_id, chunk, meta))
    return vectors

def upload_vectors_to_pinecone(vectors, batch_size=32):
    for i in tqdm(range(0, len(vectors), batch_size)):
        batch = vectors[i:i+batch_size]
        ids = [v[0] for v in batch]
        texts = [v[1] for v in batch]
        metas = [v[2] for v in batch]
        embs = model.encode(texts, show_progress_bar=False)
        index.upsert(
            vectors=[
                {"id": id, "values": emb.tolist(), "metadata": meta}
                for id, emb, meta in zip(ids, embs, metas)
            ]
        )

def main():
    print(f"인덱스 이름: {INDEX_NAME}")
    all_vectors = []
    company_dirs = [d for d in os.listdir(DOC_ROOT) if os.path.isdir(os.path.join(DOC_ROOT, d))]
    for company in tqdm(company_dirs, desc="회사별 처리"):
        company_path = os.path.join(DOC_ROOT, company)
        pdf_files = [f for f in os.listdir(company_path) if f.lower().endswith(".pdf")]
        for pdf_file in tqdm(pdf_files, desc=f"{company} PDF"):
            pdf_path = os.path.join(company_path, pdf_file)
            vectors = process_pdf(company, pdf_path)
            all_vectors.extend(vectors)
    
    print(f"총 청크 개수: {len(all_vectors)}")
    
    # 벡터 ID 중복 검사 (선택사항)
    vector_ids = [v[0] for v in all_vectors]
    unique_ids = set(vector_ids)
    if len(vector_ids) != len(unique_ids):
        print(f"경고: 중복된 벡터 ID가 {len(vector_ids) - len(unique_ids)}개 발견되었습니다.")
    
    upload_vectors_to_pinecone(all_vectors)
    print(f"Pinecone 업로드 완료 - 인덱스: {INDEX_NAME}")

if __name__ == "__main__":
    main()