# insurance_app/management/commands/import_glossary_csv.py
from __future__ import annotations
import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from insurance_app.models import GlossaryTerm
from insurance_app.utils.glossary_tools import (
    detect_lang, slugify_term, parse_list_field,
    build_short_def, normalize_category, resolve_related_terms_by_term_names,
)

class Command(BaseCommand):
    help = "CSV를 읽어 GlossaryTerm을 생성/갱신합니다."

    def add_arguments(self, parser):
        parser.add_argument("--path", type=str, required=True, help="CSV 경로")
        parser.add_argument("--dry-run", action="store_true", help="DB 미반영 미리보기")

    @transaction.atomic
    def handle(self, *args, **opts):
        csv_path = Path(opts["path"]).resolve()
        if not csv_path.exists():
            raise CommandError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

        df = pd.read_csv(csv_path, dtype=str).fillna("")
        required = {"term", "definition_ko"}
        if not required.issubset(set(df.columns)):
            raise CommandError(f"필수 컬럼 누락: {required - set(df.columns)}")

        created, updated = 0, 0
        pending_related_all = []

        for _, row in df.iterrows():
            term = row.get("term", "").strip()
            if not term:
                continue

            lang = (row.get("lang", "").strip() or detect_lang(term))
            slug_hint = row.get("slug", "").strip() or None

            existing = GlossaryTerm.objects.filter(term=term).first()
            slug = existing.slug if existing else slugify_term(term, lang=lang, slug_hint=slug_hint)

            category = normalize_category(row.get("category", ""))
            def_ko = row.get("definition_ko", "").strip()
            def_en = row.get("definition_en", "").strip()

            synonyms = parse_list_field(row.get("synonyms", ""))
            related_names = parse_list_field(row.get("related_terms", ""))

            related_slugs, pending = resolve_related_terms_by_term_names(GlossaryTerm, related_names)
            if pending:
                pending_related_all.extend([f"{term} → {x}" for x in pending])

            payload = dict(
                slug=slug,
                defaults=dict(
                    term=term,
                    short_def=build_short_def(def_ko),
                    long_def=def_ko,
                    category=category,
                    aliases=synonyms,
                    related=related_slugs,
                    meta={
                        "lang": lang,
                        "definition_en": def_en,
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
                        "related_terms_pending": pending,
                    }
                )
            )

            if opts["dry_run"]:
                self.stdout.write(f"[DRY] upsert {payload['slug']}: {term}")
                continue

            obj, is_created = GlossaryTerm.objects.update_or_create(**payload)
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY-RUN 완료 (DB 미반영)"))
            return

        self.stdout.write(self.style.SUCCESS(f"Glossary 반영 완료: 생성 {created} / 갱신 {updated}"))
        if pending_related_all:
            uniq = []
            seen = set()
            for x in pending_related_all:
                if x not in seen:
                    seen.add(x)
                    uniq.append(x)
            self.stdout.write(self.style.WARNING(
                "주의: 아래 관련어는 기존 용어로 해석되지 않아 meta.related_terms_pending에 기록되었습니다.\n"
                + "\n".join(f" - {x}" for x in uniq[:50])
                + ("\n ... (생략)" if len(uniq) > 50 else "")
            ))
