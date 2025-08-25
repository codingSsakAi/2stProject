# insurance_app/management/commands/csv_to_glossary_json.py
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from insurance_app.utils.glossary_tools import (
    detect_lang, slugify_term, parse_list_field,
    build_short_def, normalize_category,
)

class Command(BaseCommand):
    help = "CSV(템플릿)를 기존 스키마(JSON)로 변환하여 insurance_app/data/glossary.json 로 저장"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path", type=str, required=True,
            help="CSV 경로(예: insurance_app/data/glossary_template.csv)"
        )
        parser.add_argument(
            "--out", type=str, default="insurance_app/data/glossary.json",
            help="출력 JSON 경로(기본: insurance_app/data/glossary.json)"
        )

    def handle(self, *args, **opts):
        csv_path = Path(opts["path"]).resolve()
        out_path = Path(opts["out"]).resolve()
        out_dir = out_path.parent
        if not csv_path.exists():
            raise CommandError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        out_dir.mkdir(parents=True, exist_ok=True)

        df = pd.read_csv(csv_path, dtype=str).fillna("")

        required = {"term", "definition_ko"}
        if not required.issubset(set(df.columns)):
            raise CommandError(f"필수 컬럼 누락: {required - set(df.columns)}")

        items = []
        for _, row in df.iterrows():
            term = row.get("term", "").strip()
            if not term:
                continue

            lang = (row.get("lang", "").strip() or detect_lang(term))
            slug_hint = row.get("slug", "").strip() or None
            slug = slugify_term(term, lang=lang, slug_hint=slug_hint)

            long_def = row.get("definition_ko", "").strip()
            short_def = build_short_def(long_def)
            category = normalize_category(row.get("category", ""))

            aliases = parse_list_field(row.get("synonyms", ""))
            related_by_name = parse_list_field(row.get("related_terms", ""))

            # 기존 JSON 스키마: related는 "슬러그 목록"이지만,
            # 여기서는 우선 이름 그대로 슬러그화(동일 로직)하여 넣어줌.
            related = [slugify_term(x) for x in related_by_name] if related_by_name else []

            meta = {
                "lang": lang,
                "definition_en": row.get("definition_en", "").strip(),
                "english": row.get("english", "").strip(),
                "korean": row.get("korean", "").strip(),
                "notes": row.get("notes", "").strip(),
                "source_pdf": row.get("source_pdf", "").strip(),
                "first_seen_page": row.get("first_seen_page", "").strip(),
                "example_1": row.get("example_1", "").strip(),
                "example_2": row.get("example_2", "").strip(),
                "curation_status": row.get("curation_status", "").strip(),
                "reviewer": row.get("reviewer", "").strip(),
                "last_updated": row.get("last_updated", "").strip(),
            }

            items.append({
                "slug": slug,
                "term": term,
                "short_def": short_def,
                "long_def": long_def,
                "category": category,
                "aliases": aliases,
                "related": related,
                "meta": meta,
            })

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"변환 완료: {len(items)}개 → {out_path}"))
        self.stdout.write(self.style.NOTICE("이후 `python manage.py load_glossary` 실행으로 DB에 반영하세요."))
