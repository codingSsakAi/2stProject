import os
import pdfplumber
from sentence_transformers import SentenceTransformer
import pinecone
from tqdm import tqdm

# 환경변수에서 키 로드 (settings.py 또는 .env 이용)
import dotenv
dotenv.load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # ex) 'us-east-1'
INDEX_NAME = "insurance-clauses"
DOC_ROOT = os.path.join(os.path.dirname(__file__), "documents")

# 1. 임베딩 모델 준비
EMBED_MODEL = "jhgan/ko-sroberta-multitask"
model = SentenceTransformer(EMBED_MODEL)

# 2. Pinecone 초기화
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
if INDEX_NAME not in pinecone.list_indexes():
    pinecone.create_index(
        INDEX_NAME,
        dimension=768,  # ko-sroberta-multitask는 768
        metric="cosine"
    )
index = pinecone.Index(INDEX_NAME)

# 3. 텍스트 청크 함수
def chunk_text(text, max_length=500, overlap=50):
    """긴 텍스트를 max_length 단위로 오버랩 청크 분할"""
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

# 4. PDF 파싱 및 벡터 업로드
def process_pdf(company, pdf_path):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    vectors = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text or len(text.strip()) < 50:
                continue
            page_chunks = chunk_text(text)
            for idx, chunk in enumerate(page_chunks):
                meta = {
                    "company": company,
                    "file": doc_name,
                    "page": page_num,
                    "chunk_idx": idx,
                }
                vec_id = f"{company}_{doc_name}_{page_num}_{idx}"
                vectors.append((vec_id, chunk, meta))
    return vectors

def upload_vectors_to_pinecone(vectors, batch_size=32):
    """벡터 임베딩 및 pinecone 업로드 (배치 처리)"""
    for i in tqdm(range(0, len(vectors), batch_size)):
        batch = vectors[i:i+batch_size]
        ids = [v[0] for v in batch]
        texts = [v[1] for v in batch]
        metas = [v[2] for v in batch]
        embs = model.encode(texts, show_progress_bar=False)
        index.upsert(
            vectors=[
                (id, emb.tolist(), meta)
                for id, emb, meta in zip(ids, embs, metas)
            ]
        )

def main():
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
    print("Pinecone 업로드 완료")

if __name__ == "__main__":
    main()
