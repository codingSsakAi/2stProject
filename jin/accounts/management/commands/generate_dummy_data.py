import random
import json
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from accounts.models import (
    UserProfile,
    InsuranceRecommendation,
    RecommendationStatistics,
    UserBehaviorLog,
)


class Command(BaseCommand):
    help = "보험 추천 시스템을 위한 더미 데이터 생성"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=50, help="생성할 사용자 수 (기본값: 50)"
        )
        parser.add_argument(
            "--recommendations",
            type=int,
            default=200,
            help="생성할 추천 내역 수 (기본값: 200)",
        )
        parser.add_argument(
            "--behavior-logs",
            type=int,
            default=500,
            help="생성할 행동 로그 수 (기본값: 500)",
        )

    def handle(self, *args, **options):
        self.stdout.write("더미 데이터 생성을 시작합니다...")

        try:
            with transaction.atomic():
                # 1. 사용자 및 프로필 생성
                users = self.create_users_and_profiles(options["users"])

                # 2. 보험 추천 내역 생성
                recommendations = self.create_insurance_recommendations(
                    users, options["recommendations"]
                )

                # 3. 추천 통계 생성
                self.create_recommendation_statistics(recommendations)

                # 4. 사용자 행동 로그 생성
                self.create_user_behavior_logs(
                    users, recommendations, options["behavior_logs"]
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"더미 데이터 생성 완료!\n"
                    f"- 사용자: {len(users)}명\n"
                    f"- 추천 내역: {len(recommendations)}개\n"
                    f'- 행동 로그: {options["behavior_logs"]}개'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"더미 데이터 생성 중 오류 발생: {str(e)}")
            )

    def create_users_and_profiles(self, user_count):
        """사용자 및 프로필 생성"""
        self.stdout.write(f"{user_count}명의 사용자와 프로필을 생성합니다...")

        users = []
        user_profiles = []

        # 연령대별 분포 설정
        age_distribution = {
            "20대": (20, 29, 10),
            "30대": (30, 39, 15),
            "40대": (40, 49, 15),
            "50대": (50, 59, 10),
        }

        # 성별 선택지
        genders = ["M", "F"]

        # 거주 지역 선택지
        residence_areas = [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "기타",
        ]

        # 차종 선택지
        car_types = ["경차", "소형", "준중형", "중형", "대형", "SUV"]

        # 보장 수준 선택지
        coverage_levels = ["기본", "표준", "고급", "프리미엄"]

        user_id = 1

        for age_group, (min_age, max_age, count) in age_distribution.items():
            for i in range(count):
                # 사용자 생성
                username = f"user{user_id:03d}"
                email = f"{username}@example.com"

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password="password123",
                    first_name=f"사용자{user_id}",
                    last_name="테스트",
                )
                users.append(user)

                # 생년월일 계산 (랜덤)
                birth_year = random.randint(min_age, max_age)
                birth_month = random.randint(1, 12)
                birth_day = random.randint(1, 28)  # 간단하게 28일로 제한
                birth_date = date(2024 - birth_year, birth_month, birth_day)

                # 프로필 생성
                profile = UserProfile(
                    user=user,
                    birth_date=birth_date,
                    gender=random.choice(genders),
                    residence_area=random.choice(residence_areas),
                    driving_experience=random.randint(0, 20),
                    car_type=random.choice(car_types),
                    annual_mileage=random.randint(5000, 50000),
                    accident_history=random.randint(0, 3),
                    coverage_level=random.choice(coverage_levels),
                    additional_coverage_interest=random.choice([True, False]),
                )
                user_profiles.append(profile)

                user_id += 1

        # 프로필 일괄 저장
        UserProfile.objects.bulk_create(user_profiles)

        return users

    def create_insurance_recommendations(self, users, recommendation_count):
        """보험 추천 내역 생성"""
        self.stdout.write(f"{recommendation_count}개의 추천 내역을 생성합니다...")

        recommendations = []

        # 추천 모드 선택지
        recommendation_modes = ["quick", "standard", "detailed", "chatbot"]

        # 보험사 목록
        insurance_companies = [
            "삼성화재",
            "현대해상",
            "KB손보",
            "롯데손보",
            "한화손보",
            "DB손보",
            "AXA손보",
            "메리츠화재",
        ]

        # 추천 이유 템플릿
        recommendation_reasons = [
            "고객님의 운전 경력과 차종을 고려한 맞춤형 추천입니다.",
            "연령대와 지역 특성을 반영한 최적의 보험 상품입니다.",
            "사고 경력과 주행거리를 분석한 합리적인 보험료입니다.",
            "추가 특약 관심도를 고려한 포괄적인 보장을 제공합니다.",
            "경제적 부담을 최소화하면서도 충분한 보장을 받을 수 있습니다.",
        ]

        # 최근 30일 내의 날짜 범위
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        for i in range(recommendation_count):
            user = random.choice(users)
            profile = user.profile

            # 랜덤 생성 시간
            created_at = start_date + timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )

            # 추천 모드
            recommendation_mode = random.choice(recommendation_modes)

            # 사용자 프로필 스냅샷
            profile_snapshot = {
                "age": profile.get_age(),
                "gender": profile.gender,
                "residence_area": profile.residence_area,
                "driving_experience": profile.driving_experience,
                "car_type": profile.car_type,
                "annual_mileage": profile.annual_mileage,
                "accident_history": profile.accident_history,
                "coverage_level": profile.coverage_level,
            }

            # 추천 데이터 생성 (3-5개 보험사)
            num_companies = random.randint(3, 5)
            selected_companies = random.sample(insurance_companies, num_companies)

            recommendations_data = []
            for company in selected_companies:
                # 보험료 계산 (기본 50만원 + 변동요소)
                base_premium = 500000
                age_factor = 1.0 + (profile.get_age() - 30) * 0.02  # 나이에 따른 조정
                experience_factor = 1.0 - (
                    profile.driving_experience * 0.01
                )  # 경력에 따른 할인
                accident_factor = 1.0 + (
                    profile.accident_history * 0.1
                )  # 사고에 따른 할증

                premium = int(
                    base_premium * age_factor * experience_factor * accident_factor
                )

                recommendations_data.append(
                    {
                        "company": company,
                        "product_name": f"{company} 자동차보험",
                        "premium": premium,
                        "coverage_details": {
                            "대인배상": "무제한",
                            "대물배상": "5000만원",
                            "자기신체사고": "1000만원",
                            "자기차량손해": "실제손해액",
                        },
                        "discount_rate": random.randint(5, 25),
                        "recommendation_score": random.randint(70, 95),
                    }
                )

            # 선택 여부 (30% 확률로 선택)
            is_selected = random.random() < 0.3
            selected_company = random.choice(selected_companies) if is_selected else ""

            # 사용자 평가 (선택된 경우에만)
            user_rating = random.randint(4, 5) if is_selected else None
            user_feedback = "만족스러운 추천이었습니다." if is_selected else ""

            recommendation = InsuranceRecommendation(
                user=user,
                session_id=f"session_{i:06d}",
                recommendation_mode=recommendation_mode,
                user_profile_snapshot=profile_snapshot,
                recommendations_data=recommendations_data,
                recommendation_reason=random.choice(recommendation_reasons),
                is_selected=is_selected,
                selected_company=selected_company,
                user_rating=user_rating,
                user_feedback=user_feedback,
                created_at=created_at,
            )
            recommendations.append(recommendation)

        # 일괄 저장
        InsuranceRecommendation.objects.bulk_create(recommendations)

        return recommendations

    def create_recommendation_statistics(self, recommendations):
        """추천 통계 생성"""
        self.stdout.write("추천 통계를 생성합니다...")

        # 최근 30일간의 통계 생성
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        statistics = []

        for i in range(31):
            current_date = start_date + timedelta(days=i)

            # 해당 날짜의 추천 데이터 필터링
            daily_recommendations = [
                r for r in recommendations if r.created_at.date() == current_date
            ]

            if not daily_recommendations:
                continue

            # 연령대별 통계
            age_group_stats = {}
            gender_stats = {"M": 0, "F": 0}
            car_type_stats = {}
            company_preference_stats = {}
            coverage_level_stats = {}
            region_stats = {}

            total_premium = 0
            total_selections = 0

            for rec in daily_recommendations:
                profile = rec.user.profile

                # 연령대별
                age_group = profile.get_age_group()
                age_group_stats[age_group] = age_group_stats.get(age_group, 0) + 1

                # 성별
                gender_stats[profile.gender] += 1

                # 차종별
                car_type = profile.car_type
                car_type_stats[car_type] = car_type_stats.get(car_type, 0) + 1

                # 지역별
                region = profile.residence_area
                region_stats[region] = region_stats.get(region, 0) + 1

                # 보장 수준별
                coverage = profile.coverage_level
                coverage_level_stats[coverage] = (
                    coverage_level_stats.get(coverage, 0) + 1
                )

                # 보험사별 선호도 (선택된 경우)
                if rec.is_selected and rec.selected_company:
                    company_preference_stats[rec.selected_company] = (
                        company_preference_stats.get(rec.selected_company, 0) + 1
                    )

                # 평균 보험료 계산
                if rec.recommendations_data:
                    avg_premium = sum(
                        item["premium"] for item in rec.recommendations_data
                    ) / len(rec.recommendations_data)
                    total_premium += avg_premium

                if rec.is_selected:
                    total_selections += 1

            # 통계 객체 생성
            stat = RecommendationStatistics(
                date=current_date,
                age_group_stats=age_group_stats,
                gender_stats=gender_stats,
                car_type_stats=car_type_stats,
                company_preference_stats=company_preference_stats,
                coverage_level_stats=coverage_level_stats,
                region_stats=region_stats,
                total_recommendations=len(daily_recommendations),
                total_selections=total_selections,
                average_premium=(
                    total_premium / len(daily_recommendations)
                    if daily_recommendations
                    else 0
                ),
            )
            statistics.append(stat)

        # 일괄 저장
        RecommendationStatistics.objects.bulk_create(statistics)

    def create_user_behavior_logs(self, users, recommendations, log_count):
        """사용자 행동 로그 생성"""
        self.stdout.write(f"{log_count}개의 행동 로그를 생성합니다...")

        behavior_logs = []

        # 행동 타입 선택지
        behavior_types = [
            "login",
            "chat_start",
            "chat_message",
            "recommendation_request",
            "recommendation_view",
            "recommendation_select",
            "profile_update",
            "page_view",
        ]

        # 페이지 조회 대상
        pages = ["/accounts/profile/", "/chatbot/", "/accounts/profile_update/", "/"]

        # 최근 30일 내의 시간 범위
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        for i in range(log_count):
            user = random.choice(users)
            behavior_type = random.choice(behavior_types)

            # 랜덤 생성 시간
            created_at = start_time + timedelta(
                seconds=random.randint(0, int((end_time - start_time).total_seconds()))
            )

            # 행동 데이터 생성
            behavior_data = {}

            if behavior_type == "login":
                behavior_data = {
                    "ip_address": f"192.168.1.{random.randint(1, 255)}",
                    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                }
            elif behavior_type == "chat_start":
                behavior_data = {
                    "session_id": f"chat_session_{i:06d}",
                    "initial_message": "안녕하세요, 보험 추천을 받고 싶습니다.",
                }
            elif behavior_type == "chat_message":
                behavior_data = {
                    "session_id": f"chat_session_{i:06d}",
                    "message_length": random.randint(10, 100),
                    "response_time": random.randint(1, 10),
                }
            elif behavior_type == "recommendation_request":
                behavior_data = {
                    "mode": random.choice(["quick", "standard", "detailed"]),
                    "profile_complete": random.choice([True, False]),
                }
            elif behavior_type == "recommendation_view":
                if recommendations:
                    rec = random.choice(recommendations)
                    behavior_data = {
                        "recommendation_id": rec.id,
                        "view_duration": random.randint(10, 300),
                        "companies_viewed": len(rec.recommendations_data),
                    }
            elif behavior_type == "recommendation_select":
                if recommendations:
                    rec = random.choice([r for r in recommendations if r.is_selected])
                    behavior_data = {
                        "recommendation_id": rec.id,
                        "selected_company": rec.selected_company,
                        "rating": rec.user_rating,
                    }
            elif behavior_type == "profile_update":
                behavior_data = {
                    "updated_fields": random.choice(
                        ["car_type", "annual_mileage", "coverage_level"]
                    ),
                    "previous_value": "이전 값",
                    "new_value": "새로운 값",
                }
            elif behavior_type == "page_view":
                behavior_data = {
                    "page_url": random.choice(pages),
                    "referrer": "https://www.google.com",
                    "session_duration": random.randint(30, 1800),
                }

            # 세션 ID 생성
            session_id = f"session_{i:06d}"

            log = UserBehaviorLog(
                user=user,
                behavior_type=behavior_type,
                behavior_data=behavior_data,
                session_id=session_id,
                created_at=created_at,
            )
            behavior_logs.append(log)

        # 일괄 저장
        UserBehaviorLog.objects.bulk_create(behavior_logs)
