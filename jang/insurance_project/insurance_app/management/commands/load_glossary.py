# insurance_app/management/commands/load_glossary.py
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from insurance_app.models import GlossaryTerm

class Command(BaseCommand):
    help = "Load glossary terms from insurance_app/data/glossary.json"

    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parents[2] / "data" / "glossary.json"
        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f"파일을 찾을 수 없습니다: {data_path}"))
            return
        with open(data_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        created, updated = 0, 0
        for it in items:
            obj, is_created = GlossaryTerm.objects.update_or_create(
                slug=it["slug"],
                defaults={
                    "term": it["term"],
                    "short_def": it.get("short_def", ""),
                    "long_def": it.get("long_def", ""),
                    "category": it.get("category", "기타"),
                    "aliases": it.get("aliases", []),
                    "related": it.get("related", []),
                    "meta": it.get("meta", {})
                }
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1
        self.stdout.write(self.style.SUCCESS(f"용어 로드 완료: 생성 {created} / 갱신 {updated}"))
