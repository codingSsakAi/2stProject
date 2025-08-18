from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from chatbot.statistics_service import StatisticsService


class Command(BaseCommand):
    help = "보험 추천 통계 수집"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='통계 수집할 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='수집할 일수 (기본값: 1일)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='기존 통계를 강제로 덮어쓰기',
        )

    def handle(self, *args, **options):
        statistics_service = StatisticsService()
        
        # 날짜 설정
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.')
                )
                return
        else:
            target_date = date.today()

        # 일수 설정
        days = options['days']
        
        self.stdout.write(
            self.style.SUCCESS(f'통계 수집을 시작합니다. (날짜: {target_date}, 일수: {days})')
        )

        success_count = 0
        error_count = 0

        for i in range(days):
            current_date = target_date - timedelta(days=i)
            
            try:
                # 기존 통계 삭제 (force 옵션이 있거나 오늘 날짜인 경우)
                if options['force'] or current_date == date.today():
                    from accounts.models import RecommendationStatistics
                    RecommendationStatistics.objects.filter(date=current_date).delete()
                
                # 통계 수집
                stats_data = statistics_service.collect_daily_statistics(current_date)
                
                if stats_data:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'{current_date}: {stats_data["total_recommendations"]}개 추천 통계 수집 완료'
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'{current_date}: 추천 데이터가 없습니다.')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'{current_date}: 통계 수집 실패 - {str(e)}')
                )
                error_count += 1

        # 결과 요약
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'통계 수집 완료: 성공 {success_count}일, 실패 {error_count}일')
        )
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS('통계 데이터가 성공적으로 수집되었습니다.')
            )
