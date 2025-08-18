from django.core.management.base import BaseCommand
from chatbot.services import CacheService


class Command(BaseCommand):
    help = '챗봇 캐시를 완전히 초기화합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='확인 없이 캐시를 삭제합니다.',
        )

    def handle(self, *args, **options):
        cache_service = CacheService()
        
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('정말로 모든 캐시를 삭제하시겠습니까? (y/N): ')
            )
            response = input().lower()
            if response != 'y':
                self.stdout.write(self.style.ERROR('캐시 삭제가 취소되었습니다.'))
                return
        
        if cache_service.clear_cache():
            self.stdout.write(
                self.style.SUCCESS('✅ 캐시가 성공적으로 초기화되었습니다.')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ 캐시 초기화 중 오류가 발생했습니다.')
            )
