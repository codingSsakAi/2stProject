# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.db.models import Q

from insurance_app.models import GlossaryTerm
from insurance_app.utils.texts import first_sentence_ko, looks_truncated_ko

class Command(BaseCommand):
    help = "끊긴 short_def(예: '…말한', '…있')을 long_def에서 다시 추출해 복구합니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="변경 없이 요약 출력만")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        qs = GlossaryTerm.objects.all().only("id", "term", "short_def", "long_def")
        fixed = 0
        total = qs.count()
        for t in qs.iterator():
            sd = (t.short_def or "").strip()
            ld = (t.long_def or "").strip()
            if not ld:
                continue  # 원문이 없으면 스킵
            if not sd or looks_truncated_ko(sd):
                new_sd = first_sentence_ko(ld, 160)
                if new_sd and new_sd != sd:
                    if dry:
                        self.stdout.write(f"[DRY] {t.term} :: '{sd}' -> '{new_sd}'")
                    else:
                        t.short_def = new_sd
                        t.save(update_fields=["short_def"])
                        fixed += 1
        self.stdout.write(self.style.SUCCESS(f"검사 {total}건 / 갱신 {fixed}건 완료{'(DRY)' if dry else ''}"))
