import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.contrib.auth.models import User
from accounts.models import UserProfile, InsuranceRecommendation
from doc.insurance_mock_server import InsuranceMockServer


class InsuranceRecommendationService:
    """
    보험 추천 서비스 클래스
    insurance_mock_server.py를 활용하여 보험 추천 기능 제공
    """

    def __init__(self):
        self.mock_server = InsuranceMockServer()

    def get_user_profile_for_recommendation(self, user: User) -> Dict[str, Any]:
        """
        사용자 프로필을 보험 추천용 형식으로 변환
        """
        try:
            profile = user.profile
            return {
                "birth_date": profile.birth_date.strftime("%Y-%m-%d") if profile.birth_date else "1990-01-01",
                "gender": profile.gender or "M",
                "residence_area": profile.residence_area or "서울",
                "driving_experience": profile.driving_experience or 5,
                "accident_history": profile.accident_history or 0,
                "car_info": {"type": profile.car_type or "준중형"},
                "annual_mileage": profile.annual_mileage or 12000,
                "coverage_level": profile.coverage_level or "표준",
            }
        except UserProfile.DoesNotExist:
            # 프로필이 없는 경우 기본값 반환
            return {
                "birth_date": "1990-01-01",
                "gender": "M",
                "residence_area": "서울",
                "driving_experience": 5,
                "accident_history": 0,
                "car_info": {"type": "준중형"},
                "annual_mileage": 12000,
                "coverage_level": "표준",
            }

    def calculate_insurance_recommendations(
        self, user: User, mode: str = "standard"
    ) -> Dict[str, Any]:
        """
        보험 추천 계산 및 결과 저장
        """
        # 사용자 프로필 가져오기
        user_profile = self.get_user_profile_for_recommendation(user)

        # Mock 서버로 보험료 계산
        result = self.mock_server.calculate_premium(user_profile)

        # 추천 세션 ID 생성
        session_id = f"REC_{uuid.uuid4().hex[:8].upper()}"

        # 추천 결과를 데이터베이스에 저장
        recommendation = InsuranceRecommendation.objects.create(
            user=user,
            session_id=session_id,
            recommendation_mode=mode,
            user_profile_snapshot=user_profile,
            recommendations_data=result["quotes"],
            recommendation_reason=self._generate_recommendation_reason(
                result, user_profile
            ),
        )

        # 결과에 세션 ID 추가
        result["session_id"] = session_id
        result["recommendation_id"] = recommendation.id

        return result

    def _generate_recommendation_reason(
        self, result: Dict[str, Any], user_profile: Dict[str, Any]
    ) -> str:
        """
        추천 이유 생성
        """
        quotes = result["quotes"]
        if not quotes:
            return "적절한 보험 상품을 찾을 수 없습니다."

        # 최저가 보험사
        lowest_company = quotes[0]["company"]
        lowest_premium = quotes[0]["annual_premium"]

        # 가성비 최고 보험사
        best_value = result["market_analysis"]["best_value"]

        # 사용자 위험도
        risk_level = result["user_info"]["risk_level"]

        reasons = []

        # 가격 기반 추천
        reasons.append(f"최저가 보험사: {lowest_company} ({lowest_premium:,}원)")

        # 가성비 기반 추천
        if best_value != lowest_company:
            reasons.append(f"가성비 최고: {best_value}")

        # 위험도 기반 추천
        if risk_level == "높음":
            reasons.append("위험도가 높아 고급 보장을 권장합니다.")
        elif risk_level == "낮음":
            reasons.append("위험도가 낮아 기본 보장으로도 충분합니다.")

        # 연령대 기반 추천
        age_category = result["user_info"]["age_category"]
        if age_category == "young":
            reasons.append("젊은 운전자로 무사고 할인 혜택을 받을 수 있습니다.")
        elif age_category == "senior":
            reasons.append("경험 많은 운전자로 할인 혜택을 받을 수 있습니다.")

        return " | ".join(reasons)

    def get_user_recommendation_history(
        self, user: User, limit: int = 10
    ) -> List[InsuranceRecommendation]:
        """
        사용자의 추천 이력 조회
        """
        return InsuranceRecommendation.objects.filter(user=user).order_by(
            "-created_at"
        )[:limit]

    def update_recommendation_feedback(
        self, session_id: str, rating: int, feedback: str = ""
    ) -> bool:
        """
        추천 결과에 대한 사용자 피드백 업데이트
        """
        try:
            recommendation = InsuranceRecommendation.objects.get(session_id=session_id)
            recommendation.user_rating = rating
            recommendation.user_feedback = feedback
            recommendation.save()
            return True
        except InsuranceRecommendation.DoesNotExist:
            return False

    def select_insurance_company(self, session_id: str, company_name: str) -> bool:
        """
        사용자가 특정 보험사를 선택했을 때 기록
        """
        try:
            recommendation = InsuranceRecommendation.objects.get(session_id=session_id)
            recommendation.is_selected = True
            recommendation.selected_company = company_name
            recommendation.save()
            return True
        except InsuranceRecommendation.DoesNotExist:
            return False

    def get_company_detail(self, company_name: str) -> Dict[str, Any]:
        """
        보험사 상세 정보 조회
        """
        return self.mock_server.get_company_detail(company_name)

    def get_market_trends(self) -> Dict[str, Any]:
        """
        시장 동향 정보 조회
        """
        return self.mock_server.get_market_trends()

    def analyze_user_preferences(self, user: User) -> Dict[str, Any]:
        """
        사용자 선호도 분석 (ML 기능을 위한 기초 데이터)
        """
        recommendations = self.get_user_recommendation_history(user, limit=50)

        if not recommendations:
            return {"message": "추천 이력이 없습니다."}

        # 선호 보험사 분석
        company_preferences = {}
        total_recommendations = 0

        for rec in recommendations:
            if rec.recommendations_data:
                for quote in rec.recommendations_data:
                    company = quote.get("company", "")
                    if company:
                        company_preferences[company] = (
                            company_preferences.get(company, 0) + 1
                        )
                        total_recommendations += 1

        # 선호도 비율 계산
        if total_recommendations > 0:
            for company in company_preferences:
                company_preferences[company] = round(
                    company_preferences[company] / total_recommendations * 100, 1
                )

        # 평균 평가 점수
        ratings = [rec.user_rating for rec in recommendations if rec.user_rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        return {
            "total_recommendations": len(recommendations),
            "company_preferences": company_preferences,
            "average_rating": round(avg_rating, 1),
            "preferred_coverage_level": self._get_preferred_coverage_level(
                recommendations
            ),
            "preferred_price_range": self._get_preferred_price_range(recommendations),
        }

    def _get_preferred_coverage_level(
        self, recommendations: List[InsuranceRecommendation]
    ) -> str:
        """
        선호 보장 수준 분석
        """
        coverage_counts = {}

        for rec in recommendations:
            if rec.user_profile_snapshot:
                coverage = rec.user_profile_snapshot.get("coverage_level", "표준")
                coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1

        if coverage_counts:
            return max(coverage_counts, key=coverage_counts.get)
        return "표준"

    def _get_preferred_price_range(
        self, recommendations: List[InsuranceRecommendation]
    ) -> Dict[str, Any]:
        """
        선호 가격대 분석
        """
        prices = []

        for rec in recommendations:
            if rec.recommendations_data:
                for quote in rec.recommendations_data:
                    price = quote.get("annual_premium", 0)
                    if price > 0:
                        prices.append(price)

        if prices:
            return {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) // len(prices),
                "median": sorted(prices)[len(prices) // 2],
            }

        return {"min": 0, "max": 0, "average": 0, "median": 0}
