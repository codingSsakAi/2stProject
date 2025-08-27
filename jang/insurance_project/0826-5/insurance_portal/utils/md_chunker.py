# -*- coding: utf-8 -*-
"""
Feature: 보험 상식
Purpose: 파일 용도 주석 추가
Notes: 해당 파일은 보험 상식 기능에 사용됩니다.
"""
"""
Markdown(과실비율 인정기준) → JSONL 청크 변환기
- 표는 절대 분할하지 않고 table_md/table_json으로 보존
- 텍스트는 600~900자 + 140자 overlap
- 판례/법령/설명 블록을 간단히 식별(type: case|law|prose)
"""

from __future__ import annotations
import json, re, os
from typing import List, Dict, Optional
import unicodedata, hashlib


CHUNK_MIN = 600
CHUNK_MAX = 900
OVERLAP   = 140

TOPIC_KW = [
    "좌회전","우회전","직진","후진","유턴","차로변경","신호위반","보행자","자전거",
    "교차로","횡단보도","점멸신호","추돌","추월","후행","야간","시야장애","고속도로",
    "이중정차","주정차","우측통행","우선순위","간선도로","서행","급정지","무단횡단",
]

def _is_table_header(line: str) -> bool:
    # | 헤더 | 헤더 |  다음줄이  | --- | --- |  형태
    return bool(re.match(r"^\s*\|.*\|\s*$", line))

def _is_table_divider(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", line))

def _is_probably_table_block(block: List[str]) -> bool:
    # “헤더줄 + 구분선”이 연속하면 표로 간주
    for i in range(len(block) - 1):
        if _is_table_header(block[i]) and _is_table_divider(block[i+1]):
            return True
    return False

def _split_tables(md_lines: List[str]) -> List[List[str]]:
    """
    MD를 '표 블록' 단위와 '기타 블록' 단위로 대강 나눕니다.
    이후 표는 그대로, 기타는 텍스트 청크로 further split.
    """
    out: List[List[str]] = []
    i = 0
    n = len(md_lines)
    while i < n:
        # 표 시작을 만나면 표가 끝날 때까지 묶음
        if _is_table_header(md_lines[i]):
            j = i + 1
            saw_div = False
            if j < n and _is_table_divider(md_lines[j]):
                saw_div = True
                j += 1
            if saw_div:
                # 표는 빈줄 나오면 종료로 간주
                while j < n and (md_lines[j].strip() != "" or re.match(r"^\s*\|", md_lines[j])):
                    j += 1
                out.append(md_lines[i:j])
                i = j
                continue
        # 그 외: 다음 표 시작 전까지 모아서 하나의 prose 덩어리 후보
        j = i + 1
        while j < n and not _is_table_header(md_lines[j]):
            j += 1
        out.append(md_lines[i:j])
        i = j
    return out

def _detect_caption(lines: List[str]) -> Optional[str]:
    """
    표 위/인접부에 '보1', '보3', '차43-5' 같은 캡션이 있으면 ID로 사용
    """
    text = "\n".join(lines[:3])  # 상단 3줄만 탐색
    m = re.search(r"(보\s*\d+|차\s*\d+(?:-\d+)?)", text)
    if m:
        return re.sub(r"\s+", "", m.group(1)).replace("차", "cha").replace("보","bo")
    return None

def _guess_type(block_text: str) -> str:
    # 간단 휴리스틱
    if "판결" in block_text or "판례" in block_text:
        return "case"
    if "도로교통법" in block_text or "별표" in block_text or "시행규칙" in block_text or "조" in block_text[:10]:
        return "law"
    return "prose"

def _extract_topics(text: str) -> List[str]:
    found = [kw for kw in TOPIC_KW if kw in text]
    # 중복 제거, 입력 순서 유지
    seen, out = set(), []
    for k in found:
        if k not in seen:
            out.append(k); seen.add(k)
    return out

def _slug_ascii(s: str, fallback_seed: str = "") -> str:
    # 한글 등 비-ASCII 제거 → [A-Za-z0-9_.:-]만 남기고, 소문자/중복 하이픈 정리
    s_norm  = unicodedata.normalize('NFKD', s or "")
    s_ascii = s_norm.encode('ascii', 'ignore').decode('ascii')
    s_ascii = re.sub(r'[^A-Za-z0-9_.:-]+', '-', s_ascii).strip('-_.:').lower()
    s_ascii = re.sub(r'-{2,}', '-', s_ascii)
    if not s_ascii:
        h = hashlib.sha1((fallback_seed or s or "x").encode('utf-8')).hexdigest()[:8]
        s_ascii = f"chunk-{h}"
    return s_ascii[:64]  # 길이 제한


def _parse_table(table_lines: List[str]) -> Dict:
    """Markdown 표를 headers/rows 구조로 파싱"""
    # 공백 제거
    lines = [ln.rstrip() for ln in table_lines if ln.strip()]
    # 헤더/구분선/데이터
    headers, rows = [], []
    if len(lines) >= 2 and _is_table_header(lines[0]) and _is_table_divider(lines[1]):
        headers = [c.strip() for c in lines[0].strip("|").split("|")]
        for ln in lines[2:]:
            if not ln.strip().startswith("|"):
                break
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            # 패딩
            if len(cells) < len(headers):
                cells += [""] * (len(headers) - len(cells))
            rows.append(cells[:len(headers)])
    return {"headers": headers, "rows": rows}

def chunk_markdown(md_text: str, source_name: str = "output.md") -> List[Dict]:
    """
    표는 통짜 청크, 나머지는 600~900자 + overlap로 청크 생성
    chapter(상위 헤더) 추출은 단순화: 최근 등장한 ##, ###를 누적
    """
    lines = md_text.splitlines()
    blocks = _split_tables(lines)
    chunks: List[Dict] = []
    chapter_h2, chapter_h3 = "", ""

    def push_prose(text: str, base_id: str):
        if not text.strip():
            return
        # 길면 고정 길이 슬라이딩
        s = text.strip()
        start = 0
        idx = 0
        while start < len(s):
            end = min(len(s), start + CHUNK_MAX)
            # 경계 조정: 마침표/줄바꿈에서 끊기
            cut = s.rfind("。", start, end)
            if cut == -1: cut = s.rfind(".", start, end)
            if cut == -1: cut = s.rfind("\n", start, end)
            if cut == -1 or cut < start + CHUNK_MIN:
                cut = end
            piece = s[start:cut].strip()
            if piece:
                chunk_id = f"{base_id}-{idx:02d}"
                chunks.append({
                    "id": chunk_id,
                    "type": _guess_type(piece),
                    "chapter": "/".join([p for p in [chapter_h2, chapter_h3] if p]),
                    "topic": _extract_topics(piece),
                    "text": piece,
                    "source": source_name,
                })
                idx += 1
            # overlap
            start = max(cut - OVERLAP, cut)

    for block in blocks:
        # 헤더 갱신
        hdrs = [ln for ln in block if ln.startswith("#")]
        for h in hdrs:
            if h.startswith("###"):
                chapter_h3 = h.strip("# ").strip()
            elif h.startswith("##"):
                chapter_h2 = h.strip("# ").strip()
                chapter_h3 = ""  # 새 h2면 h3 초기화

        if _is_probably_table_block(block):
            table_md = "\n".join(block).strip()
            cap_id = _detect_caption(block) or _slug_ascii(chapter_h3 or chapter_h2 or "table")
            table_json = _parse_table(block)
            chunks.append({
                "id": cap_id,
                "type": "table",
                "chapter": "/".join([p for p in [chapter_h2, chapter_h3] if p]),
                "topic": _extract_topics(table_md),
                "table_md": table_md,
                "table_json": table_json,
                "text": "",  # 임베딩은 table_md를 같이 사용하거나 별도 결합 가능
                "source": source_name,
            })
        else:
            # 표가 아닌 블록 → 헤더 제거 후 prose로 합치기
            non_hdr = [ln for ln in block if not ln.startswith("#")]
            prose = "\n".join(non_hdr).strip()
            if prose:
                base_id = _slug_ascii(chapter_h3 or chapter_h2 or "prose")
                push_prose(prose, base_id)

    return chunks

def save_jsonl(chunks: List[Dict], out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for obj in chunks:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
