from django.core.management.base import BaseCommand
from chatbot.cache_service import CacheService


class Command(BaseCommand):
    help = '캐시 통계 정보를 출력합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='전체 캐시를 삭제합니다.',
        )
        parser.add_argument(
            '--query',
            type=str,
            help='특정 쿼리의 캐시 정보를 확인합니다.',
        )

    def handle(self, *args, **options):
        cache_service = CacheService()
        
        if options['clear']:
            success = cache_service.clear_cache()
            if success:
                self.stdout.write(
                    self.style.SUCCESS('전체 캐시가 성공적으로 삭제되었습니다.')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('캐시 삭제 중 오류가 발생했습니다.')
                )
            return
        
        if options['query']:
            query = options['query']
            cache_info = cache_service.get_cache_info(query)
            
            self.stdout.write(f"쿼리: {query}")
            if cache_info.get('is_cached'):
                self.stdout.write(f"캐시 상태: 캐시됨")
                self.stdout.write(f"캐시 시간: {cache_info.get('cached_at')}")
                self.stdout.write(f"TTL: {cache_info.get('ttl')}초")
                self.stdout.write(f"캐시 키: {cache_info.get('cache_key')}")
            else:
                self.stdout.write(f"캐시 상태: 캐시되지 않음")
                self.stdout.write(f"캐시 키: {cache_info.get('cache_key')}")
            return
        
        # 기본 통계 출력
        stats = cache_service.get_cache_stats()
        
        self.stdout.write("=== 캐시 통계 ===")
        self.stdout.write(f"전체 캐시 키 수: {stats.get('total_keys', 0)}")
        self.stdout.write(f"연락처 캐시 키 수: {stats.get('contact_cache_keys', 0)}")
        self.stdout.write(f"자주 묻는 질문 캐시 키 수: {stats.get('frequent_query_keys', 0)}")
        self.stdout.write(f"일반 응답 캐시 키 수: {stats.get('chat_response_keys', 0)}")
        self.stdout.write(f"캐시 크기: {stats.get('cache_size_mb', 0)}MB")
        
        self.stdout.write("\n=== 사용법 ===")
        self.stdout.write("캐시 통계 확인: python manage.py cache_stats")
        self.stdout.write("특정 쿼리 캐시 확인: python manage.py cache_stats --query '메리츠화재 연락처'")
        self.stdout.write("전체 캐시 삭제: python manage.py cache_stats --clear")
