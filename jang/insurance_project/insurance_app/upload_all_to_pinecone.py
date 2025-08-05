import os
import glob
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import PyPDF2
import unicodedata
from dotenv import load_dotenv
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "insurance-clauses"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DOCUMENTS_ROOT = os.path.join(os.path.dirname(__file__), "documents")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)
model = SentenceTransformer(EMBED_MODEL)

def to_ascii(s):
    """벡터ID용: 한글/특수문자 제거, 영어/숫자/언더바로만 변환."""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")

def chunk_text(text, chunk_size=400, overlap=100):
    tokens = text.split()
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk = " ".join(tokens[i:i+chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def parse_and_upsert_all(doc_root, batch_size=32):
    for company_folder in glob.glob(os.path.join(doc_root, "*")):
        if not os.path.isdir(company_folder):
            continue
        company_name = os.path.basename(company_folder)
        company_ascii = to_ascii(company_name)
        for pdf_file in glob.glob(os.path.join(company_folder, "*.pdf")):
            file_ascii = to_ascii(os.path.basename(pdf_file))
            print(f"처리 시작: [{company_name}] {os.path.basename(pdf_file)}")
            with open(pdf_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_idx, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    chunks = chunk_text(page_text)
                    buffer = []
                    for i, chunk in enumerate(chunks):
                        vec = model.encode(chunk).tolist()
                        meta = {
                            "company": company_name,
                            "file": os.path.basename(pdf_file),
                            "page": page_idx+1,
                            "chunk_idx": i,
                            "text": chunk
                        }
                        vector_id = f"{company_ascii}_{file_ascii}_{page_idx+1}_{i}"
                        buffer.append({
                            "id": vector_id,
                            "values": vec,
                            "metadata": meta
                        })
                        # batch_size만큼 모이면 업로드
                        if len(buffer) == batch_size:
                            index.upsert(vectors=buffer)
                            print(f"    page {page_idx+1}, {i+1}/{len(chunks)} chunks, batch {batch_size} 업로드")
                            buffer = []
                    # 남은 벡터 있으면 마지막 업로드
                    if buffer:
                        index.upsert(vectors=buffer)
                        print(f"    page {page_idx+1}, 남은 {len(buffer)}개 업로드")
    print("Pinecone 업로드 완료!")

if __name__ == "__main__":
    parse_and_upsert_all(DOCUMENTS_ROOT, batch_size=32)
