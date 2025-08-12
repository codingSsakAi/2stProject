# insurance_app/upload_all_to_pinecone.py

import os
import re
import hashlib
import unicodedata
from collections import defaultdict
from typing import List
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

import pdfplumber
from tqdm import tqdm

# -----------------------
# 선택적 OCR
# -----------------------
OCR_AVAILABLE = False
try:
    import pytesseract
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if TESSERACT_CMD and os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# -----------------------
# 임베더 어댑터
# -----------------------
USE_BACKEND = os.getenv("EMBED_BACKEND", "st").lower()  # "st" | "openai"
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")

class Embedder:
    def __init__(self, backend: str, model_name: str):
        self.backend = backend
        self.model_name = model_name
        self.dim = None
        if backend == "openai":
            from openai import OpenAI  # pip install openai
            self.client = OpenAI()
        else:
            from sentence_transformers import SentenceTransformer  # pip install sentence-transformers
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
# Pinecone (인덱스 보장)
# -----------------------
from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses-new")
NAMESPACE = os.getenv("NAMESPACE") or None
REGION = os.getenv("PINECONE_REGION", "us-east-1")

if not PINECONE_API_KEY:
    raise SystemExit("PINECONE_API_KEY가 비어 있습니다. .env를 확인하세요.")
if not INDEX_NAME:
    raise SystemExit("PINECONE_INDEX_NAME가 비어 있습니다. .env를 확인하세요.")

pc = Pinecone(api_key=PINECONE_API_KEY)

def ensure_index(index_name: str, embed_dim: int, metric: str = "cosine", region: str = "us-east-1"):
    existing = {i["name"] for i in pc.list_indexes()}
    if index_name in existing:
        idx = pc.Index(index_name)
        stats = idx.describe_index_stats()
        cur_dim = stats.get("dimension")
        print(f"[INFO] Found existing index '{index_name}'  dim={cur_dim}  vectors={stats.get('total_vector_count')}")
        if cur_dim != embed_dim:
            if os.getenv("ALLOW_INDEX_RECREATE", "0") == "1":
                print(f"[INFO] Recreating index '{index_name}' (dim {cur_dim} -> {embed_dim})")
                pc.delete_index(index_name)
                pc.create_index(
                    name=index_name,
                    dimension=embed_dim,
                    metric=metric,
                    spec=ServerlessSpec(cloud="aws", region=region),
                )
                idx = pc.Index(index_name)
                stats = idx.describe_index_stats()
                print(f"[INFO] Recreated index '{index_name}'  dim={stats.get('dimension')}")
                return idx
            raise SystemExit(
                f"Index '{index_name}' dim {cur_dim} != embed dim {embed_dim}. "
                f"ALLOW_INDEX_RECREATE=1 로 실행하거나 다른 PINECONE_INDEX_NAME을 사용하세요."
            )
        return idx
    else:
        print(f"[INFO] Creating index '{index_name}'  dim={embed_dim}")
        pc.create_index(
            name=index_name,
            dimension=embed_dim,
            metric=metric,
            spec=ServerlessSpec(cloud="aws", region=region),
        )
        idx = pc.Index(index_name)
        stats = idx.describe_index_stats()
        print(f"[INFO] Created index '{index_name}'  dim={stats.get('dimension')}")
        return idx

index = ensure_index(INDEX_NAME, EMBED_DIM, "cosine", REGION)

# -----------------------
# 설정
# -----------------------
ROOT = Path(__file__).resolve().parent
PDF2IMAGE_DPI = int(os.getenv("PDF2IMAGE_DPI", "250"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
DOC_ROOT = os.getenv("DOC_ROOT", str(ROOT / "documents"))

# -----------------------
# 텍스트 전처리/분할 (강화)
# -----------------------
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # 줄끝 하이픈 복원
    text = re.sub(r"^[\s\-–—_=·•]{3,}$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

_HANGUL = r"[가-힣]"

def _looks_spaced_hangul(s: str, thresh: float = 0.28) -> bool:
    toks = s.split()
    if not toks: return False
    single_ko = sum(1 for t in toks if len(t) == 1 and re.match(_HANGUL, t))
    return (single_ko / max(len(toks), 1)) >= thresh

def _collapse_hangul_spaces_if_needed(s: str) -> str:
    if _looks_spaced_hangul(s):
        s = re.sub(rf"(?<={_HANGUL})\s+(?={_HANGUL})", "", s)
    return s

def _collapse_repeated_words(s: str, max_keep: int = 2) -> str:
    # (보상 보상 보상 → 보상 보상)
    pattern = re.compile(r"(\b[\w가-힣]{1,20}\b)(?:\s+\1){2,}")
    while True:
        new = pattern.sub(lambda m: (" " + m.group(1)) * max_keep, s)
        if new == s:
            break
        s = new
    return s.strip()

def clean_text_strong(s: str) -> str:
    if not s: return ""
    s = normalize_text(s)
    s = re.sub(r"^[\s\-–—_=·•]{3,}$", " ", s, flags=re.MULTILINE)
    s = _collapse_hangul_spaces_if_needed(s)     # 예: 뺑 소 니 → 뺑소니
    s = _collapse_repeated_words(s, max_keep=2)  # 과도반복 축소
    s = re.sub(r"(?:[^\w\s가-힣]){3,}", " ", s)  # 기호 러시
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

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
        import kss  # 설치되어 있으면 사용
        return [s.strip() for s in kss.split_sentences(text) if s.strip()]
    except Exception:
        return _heuristic_split_ko(text)

def frequent_lines_to_drop(pages_text: list, min_len=6, ratio=0.6) -> set:
    appear_map = defaultdict(int)
    total_pages = len(pages_text)
    for t in pages_text:
        lines = {ln.strip() for ln in t.splitlines() if len(ln.strip()) >= min_len}
        for ln in lines:
            appear_map[ln] += 1
    return {ln for ln, c in appear_map.items() if c / max(total_pages, 1) >= ratio}

def remove_lines(text: str, drop_lines: set) -> str:
    if not drop_lines:
        return text
    kept = []
    for ln in text.splitlines():
        if ln.strip() in drop_lines:
            continue
        kept.append(ln)
    return "\n".join(kept)

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
    # 노이즈 차단 기준 상향
    chunks = [c for c in chunks if len(c) >= 40]
    cleaned = []
    for c in chunks:
        if _looks_spaced_hangul(c, thresh=0.33):
            continue
        toks = c.split()
        if toks and (len(set(toks)) / len(toks)) < 0.45:
            continue
        cleaned.append(c)
    return cleaned

def sanitize_for_ascii_id(text: str) -> str:
    text = unicodedata.normalize('NFD', text)
    ascii_text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    ascii_text = re.sub(r'_+', '_', ascii_text).strip('_')
    return ascii_text or "unknown"

def make_vec_id(company: str, doc_name: str, page_num: int, idx: int) -> str:
    base = f"{sanitize_for_ascii_id(company)}_{sanitize_for_ascii_id(doc_name)}_{page_num}_{idx}"
    if len(base) > 100:
        h = hashlib.md5(f"{company}_{doc_name}".encode("utf-8")).hexdigest()[:8]
        base = f"{sanitize_for_ascii_id(company)[:20]}_{h}_{page_num}_{idx}"
    return base

# -----------------------
# PDF → 청크
# -----------------------
def process_pdf(company: str, pdf_path: str):
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    all_chunks = []

    # 1차 추출 (반복 라인 파악용)
    pages_raw = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            pages_raw.append(normalize_text(t))
    drop = frequent_lines_to_drop(pages_raw, min_len=6, ratio=0.6)

    images = None
    if OCR_AVAILABLE:
        try:
            images = convert_from_path(pdf_path, dpi=PDF2IMAGE_DPI)
        except Exception:
            images = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = normalize_text(page.extract_text() or "")
            # OCR 보강(텍스트가 빈약한 경우)
            if OCR_AVAILABLE and images is not None and len(text.strip()) < 80:
                try:
                    ocr = pytesseract.image_to_string(images[page_num - 1], lang="kor+eng")
                    if len(ocr.strip()) > len(text.strip()):
                        text = normalize_text(ocr)
                except Exception:
                    pass
            text = remove_lines(text, drop)
            text = clean_text_strong(text)  # ★ 강화 정리 적용

            for idx, ch in enumerate(chunk_by_sentences(text, max_chars=750, overlap_sents=1)):
                meta = {"company": company, "file": doc_name, "page": page_num, "chunk_idx": idx, "text": ch}
                all_chunks.append((page_num, idx, ch, meta))

    # 중복 제거
    seen = set()
    deduped = []
    for page_num, idx, ch, meta in all_chunks:
        norm = re.sub(r"\s+", " ", ch.strip())
        h = hashlib.md5(norm.encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        deduped.append((page_num, idx, ch, meta))

    vectors = []
    for page_num, idx, ch, meta in deduped:
        vec_id = make_vec_id(company, doc_name, page_num, idx)
        vectors.append((vec_id, DOC_PREFIX + ch, ch, meta))  # id, embed_text, raw_text, meta
    return vectors

# -----------------------
# 업서트
# -----------------------
def upload_vectors(vectors, batch_size: int):
    for i in tqdm(range(0, len(vectors), batch_size), desc="Upserting"):
        batch = vectors[i:i+batch_size]
        ids = [x[0] for x in batch]
        embed_texts = [x[1] for x in batch]
        raw_texts = [x[2] for x in batch]
        metas = [x[3] for x in batch]

        embs = embedder.encode(embed_texts)
        for m, raw in zip(metas, raw_texts):
            m["text"] = raw

        index.upsert(
            vectors=[{"id": _id, "values": e, "metadata": m} for _id, e, m in zip(ids, embs, metas)],
            namespace=NAMESPACE
        )

# -----------------------
# main
# -----------------------
def main():
    st = index.describe_index_stats()
    print(f"Index: {INDEX_NAME} / Namespace: {NAMESPACE} / Backend: {USE_BACKEND} / Model: {EMBED_MODEL} / Dim(emb): {EMBED_DIM}")
    print(f"[INFO] Index stats -> dim={st.get('dimension')} total_vectors={st.get('total_vector_count')}")

    if not os.path.isdir(DOC_ROOT):
        raise SystemExit(f"documents 폴더를 찾을 수 없습니다: {DOC_ROOT}")

    company_dirs = [d for d in os.listdir(DOC_ROOT) if os.path.isdir(os.path.join(DOC_ROOT, d))]
    total = 0
    for company in tqdm(company_dirs, desc="회사별 처리"):
        company_path = os.path.join(DOC_ROOT, company)
        pdf_files = [f for f in os.listdir(company_path) if f.lower().endswith(".pdf")]
        for pdf_file in tqdm(pdf_files, desc=f"{company} PDF"):
            pdf_path = os.path.join(company_path, pdf_file)
            vecs = process_pdf(company, pdf_path)
            total += len(vecs)
            upload_vectors(vecs, batch_size=BATCH_SIZE)
    print(f"총 업로드 청크 수: {total}")

if __name__ == "__main__":
    main()
