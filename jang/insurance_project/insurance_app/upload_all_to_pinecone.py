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
import pandas as pd

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

import dotenv
dotenv.load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses-new")
DOC_ROOT = os.path.join(os.path.dirname(__file__), "documents")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# 1. 인덱스 초기화
# index.delete(deleteAll=True)
# print(f"인덱스 [{INDEX_NAME}]의 모든 벡터 데이터가 삭제되었습니다.")

EMBED_MODEL = "jhgan/ko-sroberta-multitask"
model = SentenceTransformer(EMBED_MODEL)

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

def sanitize_for_ascii_id(text):
    text = unicodedata.normalize('NFD', text)
    ascii_text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    ascii_text = re.sub(r'_+', '_', ascii_text)
    ascii_text = ascii_text.strip('_')
    if not ascii_text:
        ascii_text = "unknown"
    return ascii_text

def create_safe_vector_id(company, doc_name, page_num, chunk_idx, chunk_type):
    """
    type까지 id에 포함시켜 유니크하게 만듭니다.
    """
    safe_company = sanitize_for_ascii_id(company)
    safe_doc_name = sanitize_for_ascii_id(doc_name)
    base_id = f"{safe_company}_{safe_doc_name}_{page_num}_{chunk_type}_{chunk_idx}"
    if len(base_id) > 100:
        hash_part = hashlib.md5(f"{company}_{doc_name}_{chunk_type}".encode('utf-8')).hexdigest()[:8]
        base_id = f"{safe_company[:20]}_{hash_part}_{page_num}_{chunk_type}_{chunk_idx}"
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

def clean_ocr_text(text):
    text = re.sub(r'(\w)\1{2,}', r'\1', text)
    text = re.sub(r'(지급){2,}', '지급', text)
    text = re.sub(r'[\s]{3,}', ' ', text)
    text = re.sub(r'[^\w\s.,;:?!()-]', '', text)
    return text.strip()

def process_pdf(company, pdf_path):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    vectors = []
    images = convert_from_path(pdf_path, dpi=200)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # 1. 표 추출
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                try:
                    df = pd.DataFrame(table)
                    table_md = df.to_markdown(index=False)
                    meta = {
                        "company": company,
                        "file": doc_name,
                        "page": page_num,
                        "chunk_idx": t_idx,
                        "type": "table"
                    }
                    vec_id = create_safe_vector_id(company, doc_name, page_num, t_idx, "table")
                    vectors.append((vec_id, table_md, meta))
                except Exception as e:
                    print(f"[표 파싱 오류] {company}, {doc_name}, p.{page_num}: {e}")

            # 2. 본문 텍스트
            text = page.extract_text() or ""
            if text and len(text.strip()) > 50:
                page_chunks = chunk_text(text)
                for idx, chunk in enumerate(page_chunks):
                    meta = {
                        "company": company,
                        "file": doc_name,
                        "page": page_num,
                        "chunk_idx": idx,
                        "type": "text"
                    }
                    vec_id = create_safe_vector_id(company, doc_name, page_num, idx, "text")
                    vectors.append((vec_id, chunk, meta))

            # 3. OCR (본문/표 모두 거의 없을 때만)
            if (not text or len(text.strip()) < 50) and not tables:
                try:
                    img = images[page_num - 1]
                    ocr_text = pytesseract.image_to_string(img, lang="kor+eng")
                    ocr_text = clean_ocr_text(ocr_text)
                except Exception:
                    ocr_text = ""
                if ocr_text and len(ocr_text.strip()) > 30:
                    meta = {
                        "company": company,
                        "file": doc_name,
                        "page": page_num,
                        "chunk_idx": 0,
                        "type": "ocr"
                    }
                    vec_id = create_safe_vector_id(company, doc_name, page_num, 0, "ocr")
                    vectors.append((vec_id, ocr_text, meta))
    return vectors

def upload_vectors_to_pinecone(vectors, batch_size=32):
    for i in tqdm(range(0, len(vectors), batch_size)):
        batch = vectors[i:i+batch_size]
        ids = [v[0] for v in batch]
        texts = [v[1] for v in batch]
        metas = [v[2] for v in batch]
        embs = model.encode(texts, show_progress_bar=False)
        # Pinecone metadata에 text(본문)는 절대 넣지 않습니다!
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
    vector_ids = [v[0] for v in all_vectors]
    unique_ids = set(vector_ids)
    if len(vector_ids) != len(unique_ids):
        print(f"경고: 중복된 벡터 ID가 {len(vector_ids) - len(unique_ids)}개 발견되었습니다.")

    upload_vectors_to_pinecone(all_vectors)
    print(f"Pinecone 업로드 완료 - 인덱스: {INDEX_NAME}")

if __name__ == "__main__":
    main()
