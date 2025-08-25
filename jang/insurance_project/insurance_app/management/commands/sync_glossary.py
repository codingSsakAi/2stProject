# -*- coding: utf-8 -*-
import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from insurance_app.models import GlossaryTerm


class Command(BaseCommand):
    """
    glossary.json과 DB를 동기화합니다.
    - JSON에 없는 슬러그는 DB에서 삭제(정리)
    - JSON에 있는 항목은 slug 기준으로 생성/갱신
    """
    help = "Sync glossary DB with insurance_app/data/glossary.json (prune + upsert)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            default=None,
            help="JSON 경로 (기본: insurance_app/data/glossary.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제로 적용하지 않고 변경 예정 사항만 출력",
        )
        parser.add_argument(
            "--backup",
            action="store_true",
            help="삭제 대상 레코드를 JSON으로 백업",
        )

    def handle(self, *args, **opts):
        data_path = (
            Path(opts["data"]).resolve()
            if opts["data"]
            else Path(__file__).resolve().parents[2] / "data" / "glossary.json"
        )
        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f"파일을 찾을 수 없습니다: {data_path}"))
            return

        items = json.loads(data_path.read_text(encoding="utf-8"))
        keep_slugs = {it["slug"] for it in items if it.get("slug")}
        before_total = GlossaryTerm.objects.count()
        prune_qs = GlossaryTerm.objects.exclude(slug__in=keep_slugs).order_by("term")
        prune_count = prune_qs.count()

        # 백업
        if opts["backup"] and prune_count:
            backup_path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / f"glossary_pruned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            backup_data = list(
                prune_qs.values(
                    "slug",
                    "term",
                    "short_def",
                    "long_def",
                    "category",
                    "aliases",
                    "related",
                    "meta",
                )
            )
            backup_path.write_text(
                json.dumps(backup_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.stdout.write(self.style.WARNING(f"백업 저장: {backup_path}"))

        created = 0
        updated = 0

        if opts["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"[Dry-run] 삭제 예정: {prune_count}건 / 업서트 대상: {len(items)}건"
                )
            )
            return

        with transaction.atomic():
            # 1) JSON에 없는 찌꺼기 레코드 정리
            if prune_count:
                prune_qs.delete()

            # 2) JSON 업서트
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
                        "meta": it.get("meta", {}),
                    },
                )
                created += 1 if is_created else 0
                updated += 0 if is_created else 1                                       

        after_total = GlossaryTerm.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"동기화 완료 | 삭제 {prune_count} / 생성 {created} / 갱신 {updated} | 총 {after_total}건"
            )
        )
