# -*- coding: utf-8 -*-
"""
CSV 5종을 하나의 JSONL로 통합.
- 기본 원칙: 레코드(한 줄)=한 청크. (패킹 없음)
- 예외: '교통사고_협의서_안내_사항.csv'의 '내용'이 길면 문장기반 분할(400~800자, overlap 80)

입력  : ./data/*.csv
출력  : ./out/corpus.jsonl
인코딩: UTF-8(BOM 허용)
"""

import csv
import json
import os
import re
import uuid
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("./data")
OUT_DIR = Path("./out")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "corpus.jsonl"

# === 가이드 분할 파라미터 ===
GUIDE_MIN_CHUNK = 300
GUIDE_MAX_CHUNK = 700
GUIDE_OVERLAP   = 100

def norm(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\u200b", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def sent_split(text: str):
    """
    한국어/한영 혼합 문장 단위 대략 분리.
    너무 과하지 않게 마침표/물음표/느낌표 기준으로 분리.
    """
    text = norm(text)
    if not text:
        return []
    # 문장 구분자 기준 분해(구분자 보존)
    parts = re.split(r"([\.!?…]+)\s+", text)
    # parts: [chunk, sep, chunk, sep, ...]
    if len(parts) == 1:
        return [parts[0]]

    sents = []
    cur = ""
    for i, p in enumerate(parts):
        if i % 2 == 0:
            cur += p
        else:
            cur += p + " "
            sents.append(cur.strip())
            cur = ""
    if cur.strip():
        sents.append(cur.strip())
    return sents

def chunk_long_text_by_sentence(text: str,
                                min_size=GUIDE_MIN_CHUNK,
                                max_size=GUIDE_MAX_CHUNK,
                                overlap=GUIDE_OVERLAP):
    """
    문장 리스트를 이어 붙이면서 max_size를 넘기면 청크 종료.
    청크 경계에 overlap(문자수)만큼 앞부분을 겹치게 이어 붙임.
    """
    text = norm(text)
    if not text:
        return []

    if len(text) <= max_size:
        return [text]

    sents = sent_split(text)
    chunks = []
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
            buf = ""

    for sent in sents:
        # 다음 문장을 추가하면 너무 커지는지 확인
        if buf and len(buf) + 1 + len(sent) > max_size:
            flush()
            # overlap을 위해 이전 청크의 끝부분 일부를 다음 청크의 시작으로 가져옴
            if chunks:
                tail = chunks[-1][-overlap:]
                buf = tail
        # 이어 붙임
        if buf:
            buf += " " + sent
        else:
            buf = sent

    flush()

    # 마지막 청크가 너무 짧고 이전과 합쳐도 되면 합침(선택적)
    if len(chunks) >= 2 and len(chunks[-1]) < min_size:
        last = chunks.pop()
        chunks[-1] = (chunks[-1] + " " + last).strip()

    return chunks

def write_jsonl(rows):
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def build_contacts():
    path = DATA_DIR / "보험회사_연락처.csv"
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            company = norm(row.get("회사명"))
            address = norm(row.get("주소"))
            website = norm(row.get("웹사이트"))
            phone   = norm(row.get("전화번호"))
            content = "주소: {addr} | 웹사이트: {web} | 전화: {ph}".format(
                addr=address or "정보없음",
                web=website or "정보없음",
                ph=phone or "정보없음"
            )
            out.append({
                "id": f"contacts-{i}-{uuid.uuid4().hex[:8]}",
                "source_type": "contacts",
                "title": company or "보험회사 연락처",
                "content": content,
            })
    return out

def build_guide():
    path = DATA_DIR / "협의서_안내사항.csv"
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            section = norm(row.get("섹션"))
            title   = norm(row.get("제목"))
            body    = norm(row.get("내용"))

            # 길면 문장기반 분할, 아니면 1레코드=1청크
            if body and len(body) > GUIDE_MAX_CHUNK:
                chunks = chunk_long_text_by_sentence(body)
                for j, ch in enumerate(chunks):
                    out.append({
                        "id": f"guide-{i}-{j}-{uuid.uuid4().hex[:8]}",
                        "source_type": "guide",
                        "title": title or (section or "협의서 안내"),
                        "content": f"[섹션] {section or '-'} | [제목] {title or '-'}\n{ch}",
                    })
            else:
                content = f"[섹션] {section or '-'} | [제목] {title or '-'}\n{body or ''}".strip()
                out.append({
                    "id": f"guide-{i}-{uuid.uuid4().hex[:8]}",
                    "source_type": "guide",
                    "title": title or (section or "협의서 안내"),
                    "content": content,
                })
    return out

def build_terms():
    out = []
    p1 = DATA_DIR / "보험용어_정제_3시트.csv"
    if p1.exists():
        with open(p1, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                term = norm(row.get("term_clean"))
                desc = norm(row.get("description"))
                out.append({
                    "id": f"terms-{i}-{uuid.uuid4().hex[:8]}",
                    "source_type": "terms",
                    "title": term or "보험 용어",
                    "content": desc or "",
                })
    p2 = DATA_DIR / "과실비율정보포털_과실비율 용어해설(60개)_FINAL.csv"
    if p2.exists():
        with open(p2, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                term = norm(row.get("term"))
                desc = norm(row.get("description"))
                out.append({
                    "id": f"fault_terms-{i}-{uuid.uuid4().hex[:8]}",
                    "source_type": "fault_terms",
                    "title": term or "과실비율 용어",
                    "content": desc or "",
                })
    return out

def build_faq():
    path = DATA_DIR / "과실비율정보포털_과실비율 FAQ(61개)_FINAL.csv"
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            q = norm(row.get("question"))
            a = norm(row.get("answer"))
            content = f"Q. {q}\nA. {a}".strip()
            out.append({
                "id": f"faq-{i}-{uuid.uuid4().hex[:8]}",
                "source_type": "faq",
                "title": q or "FAQ",
                "content": content,
            })
    return out

def main():
    rows = []
    rows += build_contacts()
    rows += build_guide()
    rows += build_terms()
    rows += build_faq()

    # 중복 제거(title+content 기준)
    seen = set()
    uniq = []
    for r in rows:
        key = (r["title"], r["content"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    write_jsonl(uniq)
    print(f"OK - {len(uniq)} records written to {OUT_PATH}")

if __name__ == "__main__":
    main()
