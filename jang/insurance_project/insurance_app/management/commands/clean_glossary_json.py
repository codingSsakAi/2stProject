# insurance_app/management/commands/clean_glossary_json.py
from __future__ import annotations
import json, shutil
from pathlib import Path
from typing import Dict
from django.core.management.base import BaseCommand
from insurance_app.utils.ko_headword import normalize_headword, make_slug_from_korean

# 부족하거나 엉킨 항목은 여기서 정의/카테고리 보강
CURATED_DEFS = {
    "자기부담금(공제액)": (
        "사고마다 피보험자가 부담하는 금액.",
        "정액형·비율형·혼합형 등이 있으며, 자차 수리비 산정 시 공제됩니다.",
        "금액/산정",
    ),
    "피보험자": (
        "보험사고로 보상을 청구할 수 있는 사람.",
        "담보마다 범위가 달라질 수 있으며, 기명피보험자·친족피보험자·승낙피보험자·사용피보험자 등으로 세분됩니다.",
        "기타",
    ),
    "기명피보험자": (
        "증권에 피보험자로 기재된 사람.",
        "피보험자동차를 소유·사용·관리하는 자 중 보험계약자가 지정하여 증권에 기재된 사람입니다.",
        "기타",
    ),
    "피보험자동차": (
        "보험증권에 기재된 자동차.",
        "보험의 대상이 되는 자동차를 말하며, 특약 가입 여부에 따라 보장 범위가 달라질 수 있습니다.",
        "기타",
    ),
    "대인배상": (
        "대인배상Ⅰ·Ⅱ를 통칭하는 인적 손해 배상 담보군.",
        "Ⅰ은 의무담보, Ⅱ는 임의담보로 법정 한도를 초과하는 손해를 보완합니다.",
        "보장",
    ),
    "대인배상Ⅰ": (
        "의무담보로 타인의 신체 손해를 법정 한도로 보장.",
        "자동차손해배상보장법상 의무가입 담보입니다.",
        "보장",
    ),
    "대인배상Ⅱ": (
        "의무 한도를 넘는 인적 손해를 추가로 보장.",
        "대형사고에 대비해 높은 한도(무한 등) 설정이 일반적입니다.",
        "보장",
    ),
    "대물배상": (
        "타인의 재산(차량·시설물 등) 손해를 보장.",
        "‘1사고당’ 한도로 보장되며 초과분은 피보험자 부담입니다.",
        "보장",
    ),
    "무면허운전": (
        "면허가 없거나 효력이 정지된 상태에서의 운전.",
        "약관상 면책 사유에 해당하는 경우가 일반적입니다.",
        "제한/면책",
    ),
    "무보험자동차": (
        "대인담보가 없거나 한도가 부족한 가해차량 등.",
        "‘무보험자동차에 의한 상해’ 담보로 인한 손해를 보전합니다.",
        "제한/면책",
    ),
    "무보험자동차에 의한 상해": (
        "무보험/뺑소니/한도부족 가해차로 인한 인적 손해 보장.",
        "피보험자 측 인적 손해를 약관 한도 내에서 보전합니다.",
        "보장",
    ),
    "긴급출동 특약": (
        "견인·비상급유·배터리 점프 등 출동 서비스를 보장.",
        "횟수·거리·항목 제한이 있으며 세부 범위는 회사별로 다릅니다.",
        "특약",
    ),
    "법률비용지원 특약": (
        "형사합의금·변호사비·벌금 등을 보전.",
        "사건 제외사유·한도에 유의하세요.",
        "특약",
    ),
    "운전자 범위 한정": (
        "운전 가능한 사람의 범위를 제한해 보험료를 낮추는 조건.",
        "기명1인·부부·가족 등으로 설정합니다.",
        "제한/면책",
    ),
    "연령 한정": (
        "최저 운전자 연령을 제한해 보험료를 낮추는 조건.",
        "예: 만 26세 이상. 위반 시 면책 가능.",
        "제한/면책",
    ),
    "손해배상": (
        "불법행위나 채무불이행으로 발생한 손해를 금전으로 보전하는 것.",
        "자동차보험에선 대인/대물 담보로 보상합니다.",
        "보장",
    ),
    "손해배상책임": (
        "타인에게 입힌 손해를 배상해야 하는 법적 책임.",
        "대인배상Ⅰ·Ⅱ, 대물배상에서 해당 책임을 담보합니다.",
        "보장",
    ),
    "보험계약자": (
        "보험회사와 계약을 체결한 사람(보험료 납입의무자).",
        "피보험자·수익자와 동일인이 아닐 수 있습니다.",
        "기타",
    ),
    "의무보험": (
        "법령으로 가입이 의무화된 보험.",
        "자동차손해배상보장법상 대인배상Ⅰ이 여기에 해당합니다.",
        "보장",
    ),
}

# 표제어로 쓰지 않을 토막어(필요시 확장)
DROP_TERMS = {"보장"}  # '카테고리 단어'가 표제어로 들어온 경우 등

class Command(BaseCommand):
    help = "glossary.json을 표제어 정규화/병합/정의보강하여 쓰레기 항목을 제거하고 대표어로 정리합니다."

    def add_arguments(self, parser):
        parser.add_argument("--path", type=str, default="insurance_app/data/glossary.json", help="정리할 JSON 경로")
        parser.add_argument("--backup", action="store_true", help="원본을 .backup 으로 저장")

    def handle(self, *args, **opts):
        path = Path(opts["path"]).resolve()
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"파일이 없습니다: {path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        merged: Dict[str, dict] = {}
        dropped, normalized, updated_defs = [], [], []

        for item in data:
            term = (item.get("term") or "").strip()
            if not term:
                continue

            # 삭제 후보
            if term in DROP_TERMS:
                dropped.append(term)
                continue

            # 정규화
            canon, changed, reason = normalize_headword(term)
            if changed and canon != term:
                # 원래 표기는 동의어로 보존
                aliases = set(item.get("aliases") or [])
                aliases.add(term)
                item["aliases"] = sorted(list(aliases))
                item["term"] = canon
                normalized.append(f"{term} → {canon}")

            # 병합
            if canon in merged:
                dst = merged[canon]
                # 동의어 합치기
                dst_alias = set(dst.get("aliases") or [])
                src_alias = set(item.get("aliases") or [])
                dst["aliases"] = sorted(list(dst_alias | src_alias))
                # 카테고리: '기타'보다 의미 있는 값 우선
                if (dst.get("category") in (None, "", "기타")) and item.get("category"):
                    dst["category"] = item["category"]
                # 정의: 간결/명료 쪽 우선
                def pick(a, b):
                    a = (a or "").strip(); b = (b or "").strip()
                    if not a: return b
                    if not b: return a
                    # 너무 길거나 '…'가 많으면 점수 낮춤
                    def score(x): return (1 if len(x) >= 16 else 0) + (0 if "…" in x or "..." in x else 1)
                    return a if score(a) >= score(b) else b
                dst["short_def"] = pick(dst.get("short_def"), item.get("short_def"))
                dst["long_def"]  = pick(dst.get("long_def"),  item.get("long_def"))
            else:
                merged[canon] = item

        # 정의/카테고리 보강 + 슬러그 보정
        for k, v in merged.items():
            sd, ld, cat = CURATED_DEFS.get(k, (None, None, None))
            changed = False
            if sd and not (v.get("short_def") or "").strip():
                v["short_def"] = sd; changed = True
            if ld and not (v.get("long_def") or "").strip():
                v["long_def"] = ld; changed = True
            if cat and (v.get("category") in (None, "", "기타")):
                v["category"] = cat; changed = True
            if not v.get("slug"):
                v["slug"] = make_slug_from_korean(k); changed = True
            if changed: updated_defs.append(k)

        out = list(merged.values())
        if opts["backup"]:
            shutil.copy(str(path), str(path) + ".backup")
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(
            f"정리 완료: 총 {len(data)} → {len(out)} 항목. "
            f"정규화 {len(normalized)}건, 삭제 {len(dropped)}건, 정의/카테고리 보강 {len(updated_defs)}건."
        ))
        if normalized:
            self.stdout.write("예시(정규화): " + ", ".join(normalized[:10]) + (" ..." if len(normalized) > 10 else ""))
        if dropped:
            self.stdout.write("예시(삭제): " + ", ".join(dropped[:10]) + (" ..." if len(dropped) > 10 else ""))
