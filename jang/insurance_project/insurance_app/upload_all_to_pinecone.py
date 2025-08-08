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

EMBED_MODEL = "jhgan/ko-sroberta-multitask"
model = SentenceTransformer(EMBED_MODEL)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# 1. 인덱스 초기화
# index.delete(deleteAll=True)
# print(f"인덱스 [{INDEX_NAME}]의 모든 벡터 데이터가 삭제되었습니다.")
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    pc.create_index(
        name=INDEX_NAME,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )

MAX_META_BYTES = 38000  # 안전한 38KB
OVERLAP_BYTES = 800

def is_noise(text):
    """의미없는 반복, 너무 짧거나 깨진 문장, 규칙 등 거르기."""
    if not text or len(text.strip()) < 15:
        return True
    # 한글 글자 반복, 영문/숫자 반복, 쓸데없는 특수기호만 있는 것 등
    if re.search(r'([가-힣])\1{1,}', text):
        return True
    if re.search(r'([a-zA-Z0-9])\1{3,}', text):
        return True
    if re.match(r'^[-=|.]{5,}$', text):
        return True
    return False

def chunk_text_by_sentence(text, min_len=20, max_len=300):
    sents = re.split(r'(?<=[.?!])\s+|(?<=\n)', text)
    result = []
    for s in sents:
        s = s.strip()
        if is_noise(s) or len(s) < min_len:
            continue
        # 너무 길면 중간에 자르기
        while len(s) > max_len:
            result.append(s[:max_len])
            s = s[max_len:]
        if s:
            result.append(s)
    return result

def table_to_rows(table):
    rows = []
    try:
        df = pd.DataFrame(table)
        if df.shape[0] < 2 or df.shape[1] < 2:
            return []
        headers = [str(h).strip() for h in df.iloc[0].tolist()]
        for idx, row in df.iterrows():
            if idx == 0:
                continue  # skip header row
            items = [str(cell).strip() for cell in row.tolist()]
            if all(len(it) < 2 for it in items):
                continue
            row_str = ", ".join(f"{h}: {i}" for h, i in zip(headers, items))
            if not is_noise(row_str):
                rows.append(row_str)
    except Exception as e:
        print("table_to_rows error:", e)
    return rows

def sanitize_for_ascii_id(text):
    text = unicodedata.normalize('NFD', text)
    ascii_text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    ascii_text = re.sub(r'_+', '_', ascii_text)
    ascii_text = ascii_text.strip('_')
    if not ascii_text:
        ascii_text = "unknown"
    return ascii_text

def create_safe_vector_id(company, doc_name, page_num, chunk_idx, chunk_type):
    safe_company = sanitize_for_ascii_id(company)
    safe_doc_name = sanitize_for_ascii_id(doc_name)
    base_id = f"{safe_company}_{safe_doc_name}_{page_num}_{chunk_type}_{chunk_idx}"
    if len(base_id) > 100:
        hash_part = hashlib.md5(f"{company}_{doc_name}_{chunk_type}".encode('utf-8')).hexdigest()[:8]
        base_id = f"{safe_company[:20]}_{hash_part}_{page_num}_{chunk_type}_{chunk_idx}"
    return base_id

def split_text_by_bytes(text, max_bytes=MAX_META_BYTES, overlap_bytes=OVERLAP_BYTES):
    text_bytes = text.encode('utf-8')
    chunks = []
    start = 0
    while start < len(text_bytes):
        end = min(start + max_bytes, len(text_bytes))
        chunk = text_bytes[start:end].decode('utf-8', errors='ignore')
        chunks.append(chunk)
        if end == len(text_bytes):
            break
        start += max_bytes - overlap_bytes
    return chunks

def process_pdf(company, pdf_path):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    vectors = []
    images = convert_from_path(pdf_path, dpi=200)
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # 표 추출
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                rows = table_to_rows(table)
                for r_idx, row in enumerate(rows):
                    row_chunks = split_text_by_bytes(row)
                    for part_idx, chunk in enumerate(row_chunks):
                        meta = {
                            "company": company,
                            "file": doc_name,
                            "page": page_num,
                            "chunk_idx": f"{t_idx}_{r_idx}_{part_idx}",
                            "type": "table",
                            "text": chunk
                        }
                        vec_id = create_safe_vector_id(company, doc_name, page_num, meta["chunk_idx"], "table")
                        vectors.append((vec_id, chunk, meta))

            # 본문 문장별 분리
            text = page.extract_text() or ""
            sents = chunk_text_by_sentence(text)
            for idx, sent in enumerate(sents):
                chunk_list = split_text_by_bytes(sent)
                for sub_idx, sub_chunk in enumerate(chunk_list):
                    meta = {
                        "company": company,
                        "file": doc_name,
                        "page": page_num,
                        "chunk_idx": f"{idx}_{sub_idx}",
                        "type": "text",
                        "text": sub_chunk
                    }
                    vec_id = create_safe_vector_id(company, doc_name, page_num, meta["chunk_idx"], "text")
                    vectors.append((vec_id, sub_chunk, meta))

            # OCR(본문/표 모두 없을 때만)
            if (not text or len(text.strip()) < 50) and not tables:
                try:
                    img = images[page_num - 1]
                    ocr_text = pytesseract.image_to_string(img, lang="kor+eng")
                except Exception:
                    ocr_text = ""
                ocr_sents = chunk_text_by_sentence(ocr_text)
                for idx, sent in enumerate(ocr_sents):
                    chunk_list = split_text_by_bytes(sent)
                    for sub_idx, sub_chunk in enumerate(chunk_list):
                        meta = {
                            "company": company,
                            "file": doc_name,
                            "page": page_num,
                            "chunk_idx": f"ocr_{idx}_{sub_idx}",
                            "type": "ocr",
                            "text": sub_chunk
                        }
                        vec_id = create_safe_vector_id(company, doc_name, page_num, meta["chunk_idx"], "ocr")
                        vectors.append((vec_id, sub_chunk, meta))
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
    vector_ids = [v[0] for v in all_vectors]
    unique_ids = set(vector_ids)
    if len(vector_ids) != len(unique_ids):
        print(f"경고: 중복된 벡터 ID가 {len(vector_ids) - len(unique_ids)}개 발견되었습니다.")
    upload_vectors_to_pinecone(all_vectors)
    print(f"Pinecone 업로드 완료 - 인덱스: {INDEX_NAME}")

if __name__ == "__main__":
    main()
