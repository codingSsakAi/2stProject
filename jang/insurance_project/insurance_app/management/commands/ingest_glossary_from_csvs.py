# -*- coding: utf-8 -*-
"""
지정 폴더의 CSV 3종(보험용어, 과실비율 FAQ, 과실비율 용어해설)을 읽어
사전 스키마 JSON으로 변환 후, 기존 glossary.json과 병합하여
카테고리를 3개 버킷(보험용어 / 과실비율/용어해설 / 과실비율/FAQ)으로 정규화하고 DB까지 반영합니다.

사용 예:
  python manage.py ingest_glossary_from_csvs --src-dir "C:\\path\\to\\folder" --write-to-base --sync

생성 파일:
  insurance_app/data/보험용어_정제_3시트.json
  insurance_app/data/과실비율FAQ_61개.json
  insurance_app/data/과실비율_용어해설_60개.json
  insurance_app/data/glossary_3cat.json
  (옵션) insurance_app/data/glossary.json  # --write-to-base 지정 시 갱신
"""
from __future__ import annotations

import csv
import json
import re
import glob
import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, List, Iterable

from django.core.management.base import BaseCommand
from django.core.management import call_command

# 한국어 한 문장 추출/끊김 감지 (버그 수정 반영부)
from insurance_app.utils.texts import first_sentence_ko, looks_truncated_ko

# 출력 디렉터리
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# 3개 고정 버킷 라벨
BUCKET_INS = "보험용어"
BUCKET_NHI = "과실비율/용어해설"
BUCKET_FAQ = "과실비율/FAQ"


# -------- 공통 유틸 --------
def _clean(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _slugify(term: str, prefix: str = "") -> str:
    base = re.sub(r"[^a-zA-Z0-9\\-]+", "-", term.lower()).strip("-")
    if not base:
        base = hashlib.md5(term.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{base}" if prefix else base


def _to_entry(
    term: str,
    category: str,
    short_def: str,
    long_def: str,
    aliases: List[str] | None = None,
    related: List[str] | None = None,
    meta: Dict[str, Any] | None = None,
    slug_prefix: str = "",
) -> Dict[str, Any] | None:
    term = _clean(term)
    if not term:
        return None
    short_def = _clean(short_def)
    long_def = _clean(long_def)
    aliases = [_clean(a) for a in (aliases or []) if _clean(a)]
    related = [_clean(a) for a in (related or []) if _clean(a)]
    m = {"lang": "ko"}
    if meta:
        m.update(meta)
    return {
        "slug": _slugify(term, prefix=slug_prefix),
        "term": term,
        "category": category or "기타",
        "short_def": short_def,
        "long_def": long_def,
        "aliases": aliases,
        "related": related,
        "meta": m,
    }


def _read_csv_any(path: Path) -> List[Dict[str, Any]]:
    """
    인코딩 불명 CSV 안전 로더 (pandas 의존 없이 csv 모듈로 처리).
    utf-8-sig → utf-8 → cp949 → euc-kr → latin-1 순서로 시도.
    """
    encs = ("utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1")
    for enc in encs:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                rows = [dict(r) for r in reader]
                if rows:
                    return rows
                else:
                    # 헤더가 없거나 빈 경우 방어
                    f.seek(0)
                    lines = list(csv.reader(f))
                    if not lines:
                        return []
                    # 첫 행을 헤더로 가정
                    header, *body = lines
                    return [dict(zip(header, row)) for row in body]
        except Exception:
            continue
    raise RuntimeError(f"CSV 읽기 실패: {path}")


def _lower_header_map(headers: Iterable[str]) -> Dict[str, str]:
    """
    원본 헤더명 -> 소문자/공백제거 맵을 리턴 (컬럼 자동 매칭에 사용)
    """
    out: Dict[str, str] = {}
    for h in headers:
        key = re.sub(r"\s+", "", str(h)).lower()
        out[str(h)] = key
    return out


def _split_aliases(raw: str) -> List[str]:
    raw = _clean(raw)
    if not raw or raw.lower() == "nan":
        return []
    # 쉼표/슬래시/세미콜론/파이프/줄바꿈 모두 분리자로 처리
    parts = re.split(r"[,/;|\n]", raw)
    return [p.strip() for p in parts if p.strip()]


# -------- 매핑 로직 --------
def _map_insurance_terms(rows: List[Dict[str, Any]], source_name: str) -> List[dict]:
    """
    보험용어_정제_3시트.csv → 표준 엔트리 리스트
    """
    if not rows:
        return []
    lower = _lower_header_map(rows[0].keys())

    def find_col(candidates: Iterable[str], default_first=False) -> str | None:
        for orig, low in lower.items():
            if low in candidates:
                return orig
        return list(rows[0].keys())[0] if default_first else None

    term_col = find_col(("용어", "term", "표제어", "키워드", "명칭", "title"), default_first=True)
    cat_col = find_col(("분류", "카테고리", "category", "대분류", "중분류", "sheet", "시트"))
    short_col = find_col(("요약", "간단정의", "short", "한줄정의", "핵심정의"))
    long_col = find_col(("설명", "정의", "상세정의", "본문", "해설", "long", "상세설명", "content", "description"))
    alias_col = find_col(("동의어", "유의어", "별칭", "alias", "aliases", "synonyms"))

    out: List[dict] = []
    for r in rows:
        term = r.get(term_col, "")
        long_def = r.get(long_col, "") if long_col else r.get(short_col, "")
        long_def = _clean(long_def)
        # --- 버그 수정된 1문장 생성 ---
        short_def = r.get(short_col, "")
        short_def = _clean(short_def)
        if not short_def:
            short_def = first_sentence_ko(long_def, 160)
        else:
            if looks_truncated_ko(short_def) and long_def:
                short_def = first_sentence_ko(long_def, 160)

        aliases = _split_aliases(r.get(alias_col, "")) if alias_col else []
        e = _to_entry(
            term=term,
            category=BUCKET_INS,
            short_def=short_def,
            long_def=long_def,
            aliases=aliases,
            meta={"source": source_name},
            slug_prefix="gloss",
        )
        if e:
            out.append(e)
    return out


def _map_faq(rows: List[Dict[str, Any]], source_name: str) -> List[dict]:
    """
    과실비율 FAQ CSV → 표준 엔트리 리스트
    """
    if not rows:
        return []
    lower = _lower_header_map(rows[0].keys())

    def find_col(candidates: Iterable[str], default_first=False) -> str | None:
        for orig, low in lower.items():
            if low in candidates:
                return orig
        return list(rows[0].keys())[0] if default_first else None

    q_col = find_col(("질문", "question", "q", "faq질문", "제목", "문의"), default_first=True)
    a_col = find_col(("답변", "answer", "a", "faq답변", "내용", "해설", "설명"), default_first=True)

    out: List[dict] = []
    for r in rows:
        q = _clean(r.get(q_col, ""))
        a = _clean(r.get(a_col, ""))
        if not q and not a:
            continue
        term = q if q else a[:30]
        # --- 버그 수정된 1문장 생성 ---
        short_def = first_sentence_ko(a, 160)

        e = _to_entry(
            term=term,
            category=BUCKET_FAQ,
            short_def=short_def,
            long_def=a,
            aliases=[],
            meta={"source": source_name},
            slug_prefix="faq",
        )
        if e:
            out.append(e)
    return out


def _map_nhi(rows: List[Dict[str, Any]], source_name: str) -> List[dict]:
    """
    과실비율 용어해설 CSV → 표준 엔트리 리스트
    """
    if not rows:
        return []
    lower = _lower_header_map(rows[0].keys())

    def find_col(candidates: Iterable[str], default_first=False) -> str | None:
        for orig, low in lower.items():
            if low in candidates:
                return orig
        return list(rows[0].keys())[0] if default_first else None

    term_col = find_col(("용어", "term", "표제어", "키워드", "명칭", "title"), default_first=True)
    def_col = find_col(("설명", "정의", "해설", "내용", "definition", "content", "description"), default_first=True)
    alias_col = find_col(("동의어", "유의어", "별칭", "alias", "aliases", "synonyms"))

    out: List[dict] = []
    for r in rows:
        term = r.get(term_col, "")
        long_def = _clean(r.get(def_col, ""))
        # --- 버그 수정된 1문장 생성 ---
        short_def = first_sentence_ko(long_def, 160)
        aliases = _split_aliases(r.get(alias_col, "")) if alias_col else []
        e = _to_entry(
            term=term,
            category=BUCKET_NHI,
            short_def=short_def,
            long_def=long_def,
            aliases=aliases,
            meta={"source": source_name},
            slug_prefix="nhi",
        )
        if e:
            out.append(e)
    return out


# -------- 병합/정규화 --------
def _bucket_of(entry: dict) -> str:
    cat = _clean(entry.get("category", "")).lower()
    slug = _clean(entry.get("slug", "")).lower()
    src = _clean((entry.get("meta") or {}).get("source", "")).lower()
    if slug.startswith("faq-") or "faq" in cat or "faq" in src:
        return BUCKET_FAQ
    if slug.startswith("nhi-") or ("용어해설" in (entry.get("category") or "")) or ("용어해설" in (entry.get("meta") or {}).get("source", "")):
        return BUCKET_NHI
    return BUCKET_INS


def _pick_better(a: str, b: str) -> str:
    a = _clean(a)
    b = _clean(b)
    if not a:
        return b
    if not b:
        return a

    def score(x: str) -> int:
        # 좀 더 길고, 말줄임 없는 쪽 선호
        return (1 if len(x) >= 16 else 0) + (0 if "…" in x or "..." in x else 1)

    return a if score(a) >= score(b) else b


# -------- Django 커맨드 --------
class Command(BaseCommand):
    help = "CSV 3종을 읽어 JSON 변환, 병합(3 버킷 정규화) 및 DB 반영"

    def add_arguments(self, parser):
        parser.add_argument("--src-dir", required=True, help="CSV 파일이 있는 폴더 경로")
        parser.add_argument("--write-to-base", action="store_true", help="생성 결과를 glossary.json에 덮어씀")
        parser.add_argument("--sync", action="store_true", help="DB 동기화까지 수행")

    def handle(self, *args, **opts):
        src_dir = Path(opts["src_dir"]).resolve()
        if not src_dir.exists():
            self.stderr.write(self.style.ERROR(f"경로가 없습니다: {src_dir}"))
            return

        # 파일 찾기(이름 변화 대응)
        p_ins = next(iter(glob.glob(str(src_dir / "*보험용어*3시트*.csv"))), None)
        p_faq = next(iter(glob.glob(str(src_dir / "*FAQ*FINAL*.csv"))), None)
        p_nhi = next(iter(glob.glob(str(src_dir / "*용어해설*FINAL*.csv"))), None)

        if not (p_ins and p_faq and p_nhi):
            self.stderr.write(self.style.ERROR(
                "CSV 3종을 모두 찾지 못했습니다.\n"
                f"- 보험용어: {p_ins}\n- FAQ: {p_faq}\n- 용어해설: {p_nhi}\n"
                "파일명이 다르면 패턴을 맞춰 주세요."
            ))
            return

        # 1) CSV 로드
        rows_ins = _read_csv_any(Path(p_ins))
        rows_faq = _read_csv_any(Path(p_faq))
        rows_nhi = _read_csv_any(Path(p_nhi))

        # 2) CSV → JSON 엔트리 변환 (여기서 first_sentence_ko 사용)
        entries_ins = _map_insurance_terms(rows_ins, Path(p_ins).name)
        entries_faq = _map_faq(rows_faq, Path(p_faq).name)
        entries_nhi = _map_nhi(rows_nhi, Path(p_nhi).name)

        # 3) JSON 파일로 저장
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        j_ins = DATA_DIR / "보험용어_정제_3시트.json"
        j_faq = DATA_DIR / "과실비율FAQ_61개.json"
        j_nhi = DATA_DIR / "과실비율_용어해설_60개.json"
        j_ins.write_text(json.dumps(entries_ins, ensure_ascii=False, indent=2), encoding="utf-8")
        j_faq.write_text(json.dumps(entries_faq, ensure_ascii=False, indent=2), encoding="utf-8")
        j_nhi.write_text(json.dumps(entries_nhi, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(
            f"CSV→JSON 변환 완료: 보험용어 {len(entries_ins)} / FAQ {len(entries_faq)} / 용어해설 {len(entries_nhi)}"
        ))

        # 4) 기존 glossary.json 로드(있으면)
        base_path = DATA_DIR / "glossary.json"
        base_items: List[dict] = []
        if base_path.exists():
            try:
                base_items = json.loads(base_path.read_text(encoding="utf-8"))
            except Exception:
                base_items = []

        # 5) 병합 + 3버킷 정규화
        all_items = base_items + entries_ins + entries_faq + entries_nhi
        merged: Dict[str, dict] = {}

        def key_of(term: str) -> str:
            return _clean(term).lower()

        for it in all_items:
            term = _clean(it.get("term"))
            if not term:
                continue

            # 버킷 강제
            original_cat = _clean(it.get("category", ""))
            bucket = _bucket_of(it)
            if original_cat and original_cat != bucket:
                meta = it.get("meta") or {}
                if "subcategory" not in meta:
                    meta["subcategory"] = original_cat
                it["meta"] = meta
            it["category"] = bucket

            # 필드 보강 + (짧은 정의 끊김 보정)
            it["short_def"] = _clean(it.get("short_def"))
            it["long_def"] = _clean(it.get("long_def"))
            if not it["short_def"] and it["long_def"]:
                it["short_def"] = first_sentence_ko(it["long_def"], 160)
            elif looks_truncated_ko(it["short_def"]) and it["long_def"]:
                it["short_def"] = first_sentence_ko(it["long_def"], 160)

            it["aliases"] = [_clean(a) for a in (it.get("aliases") or []) if _clean(a)]
            it["related"] = [_clean(a) for a in (it.get("related") or []) if _clean(a)]
            meta = it.get("meta") or {}
            if "lang" not in meta:
                meta["lang"] = "ko"
            it["meta"] = meta
            if not _clean(it.get("slug")):
                it["slug"] = _slugify(term)

            k = key_of(term)
            if k in merged:
                dst = merged[k]
                dst["short_def"] = _pick_better(dst.get("short_def"), it.get("short_def"))
                dst["long_def"] = _pick_better(dst.get("long_def"), it.get("long_def"))
                dst["aliases"] = sorted(list(set(dst.get("aliases", []) + it.get("aliases", []))))
                dst["related"] = sorted(list(set(dst.get("related", []) + it.get("related", []))))

                cats = {dst.get("category"), it.get("category")}
                if BUCKET_FAQ in cats:
                    dst["category"] = BUCKET_FAQ
                elif BUCKET_NHI in cats:
                    dst["category"] = BUCKET_NHI
                else:
                    dst["category"] = BUCKET_INS

                # source 누적
                srcs = set()
                for m in (dst.get("meta") or {}, it.get("meta") or {}):
                    s = _clean(m.get("source"))
                    if s:
                        srcs.add(s)
                meta = dst.get("meta") or {}
                if srcs:
                    meta["source_joined"] = sorted(list(srcs))
                dst["meta"] = meta
            else:
                merged[k] = it

        final_list = sorted(merged.values(), key=lambda x: _clean(x.get("term")))
        out_path = DATA_DIR / "glossary_3cat.json"
        out_path.write_text(json.dumps(final_list, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"병합/정규화 완료: {len(final_list)}항목 → {out_path}"))

        # 6) (옵션) base로 덮어쓰기
        if opts["write_to_base"]:
            shutil.copy(str(out_path), str(base_path))
            self.stdout.write(self.style.SUCCESS(f"glossary.json 갱신: {base_path}"))

        # 7) (옵션) DB 동기화
        if opts["sync"]:
            try:
                call_command("sync_glossary")
            except Exception:
                call_command("load_glossary")
