import os
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

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
                    "company": company,
                    "file": doc_name,
                    "page": page_num,
                    "chunk_idx": idx,
                    "text": chunk  # metadata에 텍스트도 저장
                }
                vec_id = f"{company}_{doc_name}_{page_num}_{idx}"
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
    upload_vectors_to_pinecone(all_vectors)
    print(f"Pinecone 업로드 완료 - 인덱스: {INDEX_NAME}")

if __name__ == "__main__":
    main()