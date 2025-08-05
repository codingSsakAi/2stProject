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
from sentence_transformers import SentenceTransformer
from tqdm import tqdm  # 진행률 표시 + ETA

PDF_FOLDER = "./dataset_pdf"
OUTPUT_JSON = "./pdf_extracted.json"
CHUNK_SIZE = 500
FAISS_INDEX = "./faiss_index.index"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 임베딩 모델 로드
embed_model = SentenceTransformer(EMBED_MODEL)

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
    pix = page.get_pixmap(dpi=200)
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

# ========== FAISS 로컬 벡터DB ==========
def init_faiss(dimension=384):
    if os.path.exists(FAISS_INDEX):
        index = faiss.read_index(FAISS_INDEX)
    else:
        index = faiss.IndexFlatL2(dimension)
    return index

def save_faiss(index):
    faiss.write_index(index, FAISS_INDEX)

# ========== 메인 파이프라인 ==========
def process_pdf(pdf_path, faiss_index):
    file_name = Path(pdf_path).stem
    print(f"\n📄 처리 중: {file_name}")

    results = []
    text_pages = extract_text_pymupdf(pdf_path)
    total_pages = len(text_pages)
    ocr_count = 0  # ✅ OCR 적용된 페이지 카운터

    # tqdm 진행률 바 + ETA 표시
    for p in tqdm(text_pages, desc=f"🔍 OCR 진행 ({file_name})", unit="page"):
        page_num, text = p["page"], p["text"]

        # OCR 적용 조건
        if len(text) < 30:
            ocr_count += 1
            print(f"   ➡ OCR 적용: {page_num}p ({ocr_count}/{total_pages} OCR 완료)")
            text = ocr_page(pdf_path, page_num)

        results.append({
            "type": "text",
            "file_name": file_name,
            "page": page_num,
            "content": text,
            "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    print(f"📊 {file_name}: OCR 적용된 페이지 {ocr_count}/{total_pages}\n")

    # 표 추출
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

    # 텍스트 임베딩 → FAISS 저장
    for item in results:
        if item["type"] == "text" and item["content"]:
            chunks = chunk_text(item["content"])
            vectors = embed_model.encode(chunks, convert_to_numpy=True)
            faiss_index.add(vectors)

    return results

def main():
    faiss_index = init_faiss()
    pdf_files = list(Path(PDF_FOLDER).glob("*.pdf"))
    if not pdf_files:
        print("❌ PDF 파일이 없습니다.")
        return

    all_data = []
    print(f"\n🔄 총 {len(pdf_files)}개 PDF 처리 시작...\n")

    for i, pdf in enumerate(pdf_files, start=1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf.name} 처리 중...")
        extracted = process_pdf(pdf, faiss_index)
        all_data.extend(extracted)

    # JSON 저장
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    save_faiss(faiss_index)

    # ✅ 전체 완료 알림
    print(f"\n✅ 모든 PDF 처리 및 임베딩 완료!")
    print(f"💾 JSON 저장: {OUTPUT_JSON}")
    print(f"💾 FAISS 벡터DB 저장: {FAISS_INDEX}")
    print("🔔 알림: 전체 작업이 성공적으로 끝났습니다!")

if __name__ == "__main__":
    main()
