import os
import re
import unicodedata
import hashlib
from typing import List

import dotenv
dotenv.load_dotenv()

import pdfplumber
from tqdm import tqdm

# -----------------------
# 임베더 어댑터
# -----------------------
USE_BACKEND = os.getenv("EMBED_BACKEND", "st").lower()
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")

class Embedder:
    def __init__(self, backend: str, model_name: str):
        self.backend = backend
        self.model_name = model_name
        self.dim = None
        if backend == "openai":
            from openai import OpenAI
            self.client = OpenAI()
        else:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.dim = self.model.get_sentence_embedding_dimension()
    def get_dimension(self) -> int:
        if self.dim is not None:
            return self.dim
        if self.backend == "openai":
            probe = self.client.embeddings.create(model=self.model_name, input="dim probe")
            self.dim = len(probe.data[0].embedding)
            return self.dim
        return self.model.get_sentence_embedding_dimension()
    def encode(self, texts: List[str]) -> List[List[float]]:
        if self.backend == "openai":
            resp = self.client.embeddings.create(model=self.model_name, input=texts)
            return [d.embedding for d in resp.data]
        else:
            return self.model.encode(texts, show_progress_bar=False).tolist()

def is_e5(name: str) -> bool:
    return "e5" in name.lower()

DOC_PREFIX = "passage: " if (USE_BACKEND == "st" and is_e5(EMBED_MODEL)) else ""
Q_PREFIX   = "query: "   if (USE_BACKEND == "st" and is_e5(EMBED_MODEL)) else ""

embedder = Embedder(USE_BACKEND, EMBED_MODEL)
EMBED_DIM = embedder.get_dimension()

# -----------------------
# Pinecone
# -----------------------
from pinecone import Pinecone, ServerlessSpec
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses-new")
NAMESPACE = os.getenv("NAMESPACE") or None
REGION = os.getenv("PINECONE_REGION", "us-east-1")

pc = Pinecone(api_key=PINECONE_API_KEY)
existing_indexes = {i["name"] for i in pc.list_indexes()}
if INDEX_NAME not in existing_indexes:
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=REGION),
    )
index = pc.Index(INDEX_NAME)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
DOC_ROOT = os.path.join(os.path.dirname(__file__), "documents")

# -----------------------
# 전처리/분할
# -----------------------
def normalize_text(t: str) -> str:
    t = unicodedata.normalize("NFC", t or "")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def _heuristic_split_ko(text: str) -> list:
    sents, buf = [], []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        buf.append(ch)
        end = False
        if ch in ".?!":
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < n else ""
            if not (prev.isdigit() and nxt.isdigit()):
                end = True
            if ch == "." and i >= 1 and text[i - 1] == "다":
                end = True
        if end:
            j = i + 1
            while j < n and text[j].isspace():
                buf.append(text[j]); j += 1
            i = j - 1
            sent = "".join(buf).strip()
            if sent:
                sents.append(sent)
            buf = []
        i += 1
    tail = "".join(buf).strip()
    if tail:
        sents.append(tail)
    return sents

def split_sentences_ko(text: str) -> list:
    try:
        import kss
        return [s.strip() for s in kss.split_sentences(text) if s.strip()]
    except Exception:
        return _heuristic_split_ko(text)

def chunk_by_sentences(text: str, max_chars=750, overlap_sents=1) -> list:
    sents = split_sentences_ko(text)
    chunks, buf, cur = [], [], 0
    for s in sents:
        if cur + len(s) + 1 > max_chars and buf:
            chunks.append(" ".join(buf).strip())
            buf = buf[-overlap_sents:] if overlap_sents else []
            cur = sum(len(x) for x in buf)
        buf.append(s); cur += len(s) + 1
    if buf:
        chunks.append(" ".join(buf).strip())
    return [c for c in chunks if len(c) >= 30]

def process_pdf(company, pdf_path):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    vectors = []
    # 반복라인 제거 후보
    with pdfplumber.open(pdf_path) as pdf:
        pages = [normalize_text(p.extract_text() or "") for p in pdf.pages]
        lines_per = [set(ln for ln in x.splitlines() if len(ln.strip()) >= 6) for x in pages]
        freq = {}
        for lines in lines_per:
            for ln in lines:
                freq[ln] = freq.get(ln, 0) + 1
        drop = {ln for ln, c in freq.items() if c / max(len(pages), 1) >= 0.6}
    # 본 처리
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = normalize_text(page.extract_text() or "")
            # 공통 라인 제거
            kept = []
            for ln in text.splitlines():
                if ln.strip() in drop:
                    continue
                kept.append(ln)
            text = "\n".join(kept).strip()
            for idx, ch in enumerate(chunk_by_sentences(text)):
                vec_id = f"{company}_{doc_name}_{page_num}_{idx}"
                meta = {"company": company, "file": doc_name, "page": page_num, "chunk_idx": idx, "text": ch}
                vectors.append((vec_id, DOC_PREFIX + ch, meta))
    return vectors

def upsert(vectors):
    for i in tqdm(range(0, len(vectors), BATCH_SIZE), desc="Upserting"):
        batch = vectors[i:i+BATCH_SIZE]
        ids = [x[0] for x in batch]
        embed_texts = [x[1] for x in batch]
        metas = [x[2] for x in batch]
        embs = embedder.encode(embed_texts)
        index.upsert(
            vectors=[{"id": _id, "values": e, "metadata": m} for _id, e, m in zip(ids, embs, metas)],
            namespace=NAMESPACE
        )

def main():
    print(f"Index: {INDEX_NAME} / Namespace: {NAMESPACE} / Backend: {USE_BACKEND} / Model: {EMBED_MODEL} / Dim: {EMBED_DIM}")
    for company in tqdm([d for d in os.listdir(DOC_ROOT) if os.path.isdir(os.path.join(DOC_ROOT, d))], desc="회사별 처리"):
        cpath = os.path.join(DOC_ROOT, company)
        for f in tqdm([x for x in os.listdir(cpath) if x.lower().endswith('.pdf')], desc=f"{company} PDF"):
            vecs = process_pdf(company, os.path.join(cpath, f))
            upsert(vecs)
    print("완료")

if __name__ == "__main__":
    main()
