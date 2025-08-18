import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from accounts.models import (
    UserProfile, 
    InsuranceRecommendation, 
    RecommendationStatistics,
    UserBehaviorLog
)

logger = logging.getLogger(__name__)


class StatisticsService:
    """보험 추천 통계 수집 및 분석 서비스"""

    def __init__(self):
        self.cache_timeout = 3600  # 1시간 캐시

    def collect_daily_statistics(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """일일 통계 수집"""
        if target_date is None:
            target_date = date.today()

        # 기존 통계가 있으면 삭제
        RecommendationStatistics.objects.filter(date=target_date).delete()

        # 해당 날짜의 추천 데이터 조회 (시간대 적용)
        from django.utils import timezone
        start_datetime = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        recommendations = InsuranceRecommendation.objects.filter(
            created_at__range=(start_datetime, end_datetime)
        )

        if not recommendations.exists():
            logger.info(f"{target_date}에 추천 데이터가 없습니다.")
            return {}

        # 통계 데이터 수집
        stats_data = {
            'date': target_date,
            'age_group_stats': self._collect_age_group_stats(recommendations),
            'gender_stats': self._collect_gender_stats(recommendations),
            'car_type_stats': self._collect_car_type_stats(recommendations),
            'company_preference_stats': self._collect_company_preference_stats(recommendations),
            'coverage_level_stats': self._collect_coverage_level_stats(recommendations),
            'region_stats': self._collect_region_stats(recommendations),
            'total_recommendations': recommendations.count(),
            'total_selections': recommendations.filter(is_selected=True).count(),
            'average_premium': self._calculate_average_premium(recommendations),
        }

        # 통계 저장
        statistics = RecommendationStatistics.objects.create(**stats_data)
        
        # 캐시 무효화
        self._clear_statistics_cache()
        
        logger.info(f"{target_date} 통계 수집 완료: {stats_data['total_recommendations']}개 추천")
        return stats_data

    def _collect_age_group_stats(self, recommendations) -> Dict[str, Any]:
        """연령대별 통계 수집"""
        age_groups = {}
        
        for rec in recommendations:
            if rec.user_profile_snapshot:
                age = rec.user_profile_snapshot.get('age')
                if age:
                    age_group = self._get_age_group(age)
                    age_groups[age_group] = age_groups.get(age_group, 0) + 1

        return {
            'distribution': age_groups,
            'total': sum(age_groups.values()),
            'most_popular': max(age_groups.items(), key=lambda x: x[1])[0] if age_groups else None
        }

    def _collect_gender_stats(self, recommendations) -> Dict[str, Any]:
        """성별 통계 수집"""
        gender_stats = {'M': 0, 'F': 0}
        
        for rec in recommendations:
            if rec.user_profile_snapshot:
                gender = rec.user_profile_snapshot.get('gender')
                if gender in gender_stats:
                    gender_stats[gender] += 1

        return {
            'distribution': gender_stats,
            'total': sum(gender_stats.values()),
            'male_percentage': (gender_stats['M'] / sum(gender_stats.values()) * 100) if sum(gender_stats.values()) > 0 else 0,
            'female_percentage': (gender_stats['F'] / sum(gender_stats.values()) * 100) if sum(gender_stats.values()) > 0 else 0
        }

    def _collect_car_type_stats(self, recommendations) -> Dict[str, Any]:
        """차종별 통계 수집"""
        car_types = {}
        
        for rec in recommendations:
            if rec.user_profile_snapshot:
                car_type = rec.user_profile_snapshot.get('car_type')
                if car_type:
                    car_types[car_type] = car_types.get(car_type, 0) + 1

        return {
            'distribution': car_types,
            'total': sum(car_types.values()),
            'most_popular': max(car_types.items(), key=lambda x: x[1])[0] if car_types else None
        }

    def _collect_company_preference_stats(self, recommendations) -> Dict[str, Any]:
        """보험사별 선호도 통계 수집"""
        company_stats = {}
        selected_companies = {}
        
        for rec in recommendations:
            # 추천된 보험사들
            if rec.recommendations_data:
                for rec_data in rec.recommendations_data:
                    company = rec_data.get('company', 'Unknown')
                    company_stats[company] = company_stats.get(company, 0) + 1
            
            # 선택된 보험사
            if rec.is_selected and rec.selected_company:
                selected_companies[rec.selected_company] = selected_companies.get(rec.selected_company, 0) + 1

        return {
            'recommended_companies': company_stats,
            'selected_companies': selected_companies,
            'most_recommended': max(company_stats.items(), key=lambda x: x[1])[0] if company_stats else None,
            'most_selected': max(selected_companies.items(), key=lambda x: x[1])[0] if selected_companies else None
        }

    def _collect_coverage_level_stats(self, recommendations) -> Dict[str, Any]:
        """보장 수준별 통계 수집"""
        coverage_stats = {}
        
        for rec in recommendations:
            if rec.user_profile_snapshot:
                coverage = rec.user_profile_snapshot.get('coverage_level')
                if coverage:
                    coverage_stats[coverage] = coverage_stats.get(coverage, 0) + 1

        return {
            'distribution': coverage_stats,
            'total': sum(coverage_stats.values()),
            'most_popular': max(coverage_stats.items(), key=lambda x: x[1])[0] if coverage_stats else None
        }

    def _collect_region_stats(self, recommendations) -> Dict[str, Any]:
        """지역별 통계 수집"""
        region_stats = {}
        
        for rec in recommendations:
            if rec.user_profile_snapshot:
                region = rec.user_profile_snapshot.get('residence_area')
                if region:
                    region_stats[region] = region_stats.get(region, 0) + 1

        return {
            'distribution': region_stats,
            'total': sum(region_stats.values()),
            'most_popular': max(region_stats.items(), key=lambda x: x[1])[0] if region_stats else None
        }

    def _calculate_average_premium(self, recommendations) -> Optional[float]:
        """평균 보험료 계산"""
        total_premium = 0
        count = 0
        
        for rec in recommendations:
            if rec.recommendations_data:
                for rec_data in rec.recommendations_data:
                    premium = rec_data.get('premium')
                    if premium and isinstance(premium, (int, float)):
                        total_premium += premium
                        count += 1

        return total_premium / count if count > 0 else None

    def _get_age_group(self, age: int) -> str:
        """나이를 연령대 그룹으로 변환"""
        if age < 20:
            return "10대"
        elif age < 30:
            return "20대"
        elif age < 40:
            return "30대"
        elif age < 50:
            return "40대"
        elif age < 60:
            return "50대"
        else:
            return "60대 이상"

    def get_statistics_for_user(self, user) -> Dict[str, Any]:
        """사용자에게 보여줄 통계 데이터 조회"""
        cache_key = f"user_statistics_{user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        # 최근 30일 통계
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        recent_stats = RecommendationStatistics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('-date')

        if not recent_stats.exists():
            # 통계가 없으면 생성
            self.collect_daily_statistics()

        # 통계 데이터 집계
        aggregated_stats = self._aggregate_recent_statistics(recent_stats)
        
        # 캐시 저장
        cache.set(cache_key, aggregated_stats, self.cache_timeout)
        
        return aggregated_stats

    def _aggregate_recent_statistics(self, recent_stats) -> Dict[str, Any]:
        """최근 통계 데이터 집계"""
        aggregated = {
            'age_groups': {},
            'genders': {'M': 0, 'F': 0},
            'car_types': {},
            'companies': {},
            'coverage_levels': {},
            'regions': {},
            'total_recommendations': 0,
            'total_selections': 0,
            'average_premium': 0,
            'selection_rate': 0
        }

        total_premium = 0
        premium_count = 0

        for stat in recent_stats:
            # 연령대별 집계
            if stat.age_group_stats:
                for age_group, count in stat.age_group_stats.get('distribution', {}).items():
                    aggregated['age_groups'][age_group] = aggregated['age_groups'].get(age_group, 0) + count

            # 성별 집계
            if stat.gender_stats:
                gender_dist = stat.gender_stats.get('distribution', {})
                aggregated['genders']['M'] += gender_dist.get('M', 0)
                aggregated['genders']['F'] += gender_dist.get('F', 0)

            # 차종별 집계
            if stat.car_type_stats:
                for car_type, count in stat.car_type_stats.get('distribution', {}).items():
                    aggregated['car_types'][car_type] = aggregated['car_types'].get(car_type, 0) + count

            # 보험사별 집계
            if stat.company_preference_stats:
                selected_companies = stat.company_preference_stats.get('selected_companies', {})
                for company, count in selected_companies.items():
                    aggregated['companies'][company] = aggregated['companies'].get(company, 0) + count

            # 보장 수준별 집계
            if stat.coverage_level_stats:
                for coverage, count in stat.coverage_level_stats.get('distribution', {}).items():
                    aggregated['coverage_levels'][coverage] = aggregated['coverage_levels'].get(coverage, 0) + count

            # 지역별 집계
            if stat.region_stats:
                for region, count in stat.region_stats.get('distribution', {}).items():
                    aggregated['regions'][region] = aggregated['regions'].get(region, 0) + count

            # 총계
            aggregated['total_recommendations'] += stat.total_recommendations
            aggregated['total_selections'] += stat.total_selections

            # 평균 보험료 계산
            if stat.average_premium:
                total_premium += float(stat.average_premium)
                premium_count += 1

        # 평균 보험료 계산
        if premium_count > 0:
            aggregated['average_premium'] = total_premium / premium_count

        # 선택률 계산
        if aggregated['total_recommendations'] > 0:
            aggregated['selection_rate'] = (aggregated['total_selections'] / aggregated['total_recommendations']) * 100

        return aggregated

    def log_user_behavior(self, user, behavior_type: str, behavior_data: Dict = None, session_id: str = ""):
        """사용자 행동 로그 기록"""
        try:
            UserBehaviorLog.objects.create(
                user=user,
                behavior_type=behavior_type,
                behavior_data=behavior_data or {},
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"사용자 행동 로그 기록 실패: {e}")

    def _clear_statistics_cache(self):
        """통계 캐시 무효화"""
        try:
            # Redis나 다른 캐시 백엔드가 있는 경우
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern("user_statistics_*")
            else:
                # LocMemCache의 경우 전체 캐시 삭제
                cache.clear()
        except Exception as e:
            logger.warning(f"캐시 무효화 실패: {e}")

    def get_trending_insights(self) -> List[Dict[str, Any]]:
        """트렌딩 인사이트 생성"""
        insights = []
        
        # 최근 7일 통계
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        recent_stats = RecommendationStatistics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('-date')

        if not recent_stats.exists():
            return insights

        # 인기 보험사
        company_stats = {}
        for stat in recent_stats:
            if stat.company_preference_stats:
                selected_companies = stat.company_preference_stats.get('selected_companies', {})
                for company, count in selected_companies.items():
                    company_stats[company] = company_stats.get(company, 0) + count

        if company_stats:
            top_company = max(company_stats.items(), key=lambda x: x[1])
            insights.append({
                'type': 'popular_company',
                'title': '가장 인기 있는 보험사',
                'content': f'{top_company[0]}가 가장 많이 선택되었습니다.',
                'data': top_company
            })

        # 인기 차종
        car_stats = {}
        for stat in recent_stats:
            if stat.car_type_stats:
                for car_type, count in stat.car_type_stats.get('distribution', {}).items():
                    car_stats[car_type] = car_stats.get(car_type, 0) + count

        if car_stats:
            top_car = max(car_stats.items(), key=lambda x: x[1])
            insights.append({
                'type': 'popular_car',
                'title': '가장 많은 추천 차종',
                'content': f'{top_car[0]} 차종이 가장 많이 추천되었습니다.',
                'data': top_car
            })

        return insights
