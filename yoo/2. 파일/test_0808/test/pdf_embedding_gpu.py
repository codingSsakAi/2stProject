
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import camelot
import re
import json
from pathlib import Path
from datetime import datetime
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

PDF_FOLDER = "./dataset_pdf"
OUTPUT_JSON = "./pdf_extracted.json"
CHUNK_SIZE = 500
FAISS_INDEX = "./faiss_index.index"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# GPU 임베딩 모델 로드
embed_model = SentenceTransformer(EMBED_MODEL, device="cuda")

# ========== 유틸 ==========
def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text_pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        text_pages.append({"page": page_num, "text": text})
    return text_pages

def ocr_page(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num-1]
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(img, lang="kor+eng").strip()
    return text

def extract_tables(pdf_path):
    tables_data = []
    try:
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
        for t in tables:
            data = {
                "page": t.page,
                "columns": t.df.iloc[0].tolist(),
                "rows": t.df.iloc[1:].values.tolist()
            }
            tables_data.append(data)
    except Exception as e:
        print(f"[WARN] 표 추출 실패: {e}")
    return tables_data

def chunk_text(text, max_len=CHUNK_SIZE):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < max_len:
            current += " " + s
        else:
            chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks

# ========== GPU FAISS ==========
def init_faiss(dimension=384):
    res = faiss.StandardGpuResources()
    if os.path.exists(FAISS_INDEX):
        index_cpu = faiss.read_index(FAISS_INDEX)
        index_gpu = faiss.index_cpu_to_gpu(res, 0, index_cpu)
        return index_gpu
    else:
        index_cpu = faiss.IndexFlatL2(dimension)
        index_gpu = faiss.index_cpu_to_gpu(res, 0, index_cpu)
        return index_gpu

def save_faiss(index):
    index_cpu = faiss.index_gpu_to_cpu(index)
    faiss.write_index(index_cpu, FAISS_INDEX)

# ========== 메인 파이프라인 ==========
def process_pdf(pdf_path, faiss_index):
    file_name = Path(pdf_path).stem
    print(f"\n📄 처리 중: {file_name}")
    results = []
    text_pages = extract_text_pymupdf(pdf_path)

    ocr_pages = 0
    pbar = tqdm(text_pages, desc=f"🔍 OCR 진행 ({file_name})", unit="page")
    for p in pbar:
        page_num, text = p["page"], p["text"]
        if len(text) < 30:
            text = ocr_page(pdf_path, page_num)
            ocr_pages += 1
            print(f"  ➡ OCR 적용: {page_num}p ({ocr_pages}/{len(text_pages)} OCR 완료)")
        results.append({
            "type": "text",
            "file_name": file_name,
            "page": page_num,
            "content": text,
            "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    print(f"📊 {file_name}: OCR 적용된 페이지 {ocr_pages}/{len(text_pages)}")

    tables = extract_tables(pdf_path)
    for t in tables:
        results.append({
            "type": "table",
            "file_name": file_name,
            "page": t["page"],
            "columns": t["columns"],
            "rows": t["rows"],
            "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    print(f"⚡ 임베딩 및 FAISS 추가 중 ({file_name})...")
    for item in tqdm(results, desc="임베딩 진행", unit="item"):
        if item["type"] == "text" and item["content"]:
            chunks = chunk_text(item["content"])
            for chunk in chunks:
                vector = embed_model.encode([chunk], convert_to_numpy=True, device="cuda")
                faiss_index.add(vector)

    return results

def main():
    faiss_index = init_faiss()
    pdf_files = list(Path(PDF_FOLDER).glob("*.pdf"))
    print(f"\n🔄 총 {len(pdf_files)}개 PDF 처리 시작...")
    all_data = []

    for i, pdf in enumerate(pdf_files, start=1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf.name} 처리 중...")
        extracted = process_pdf(pdf, faiss_index)
        all_data.extend(extracted)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    save_faiss(faiss_index)

    print(f"\n✅ PDF 처리 완료! JSON 저장: {OUTPUT_JSON}")
    print(f"✅ 로컬 GPU FAISS 벡터DB 저장: {FAISS_INDEX}")

if __name__ == "__main__":
    main()
