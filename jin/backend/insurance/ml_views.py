"""
ML 추천 시스템 API 뷰
보험 상품 추천을 위한 ML 기반 API 엔드포인트
"""

import logging
from typing import Dict, Any, List
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import json
from django.db.models import Count

from .ml_service import MLRecommendationService
from users.models import UserProfile

# 로깅 설정
logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def generate_ml_recommendations(request):
    """ML 기반 보험 추천 생성"""
    try:
        data = request.data
        user_id = data.get("user_id")
        user_profile = data.get("user_profile", {})

        if not user_id:
            return Response(
                {"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        # ML 추천 서비스 초기화
        ml_service = MLRecommendationService()

        # 추천 생성
        recommendations = ml_service.generate_recommendations(user_id, user_profile)

        return Response({"success": True, "recommendations": recommendations})

    except Exception as e:
        logger.error(f"ML 추천 생성 실패: {e}")
        return Response(
            {"error": f"추천 생성 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_recommendation_history(request):
    """사용자 추천 이력 조회"""
    try:
        user_id = request.GET.get("user_id")

        if not user_id:
            return Response(
                {"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        ml_service = MLRecommendationService()
        history = ml_service.get_recommendation_history(int(user_id))

        return Response({"success": True, "history": history})

    except Exception as e:
        logger.error(f"추천 이력 조회 실패: {e}")
        return Response(
            {"error": f"이력 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def update_recommendation_feedback(request):
    """추천 피드백 업데이트"""
    try:
        data = request.data
        recommendation_id = data.get("recommendation_id")
        feedback = data.get("feedback", "")

        if not recommendation_id:
            return Response(
                {"error": "추천 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        ml_service = MLRecommendationService()
        ml_service.update_user_feedback(int(recommendation_id), feedback)

        return Response({"success": True, "message": "피드백이 업데이트되었습니다."})

    except Exception as e:
        logger.error(f"피드백 업데이트 실패: {e}")
        return Response(
            {"error": f"피드백 업데이트 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_recommendation_stats(request):
    """추천 시스템 통계 조회"""
    try:
        ml_service = MLRecommendationService()
        stats = ml_service.get_recommendation_stats()

        return Response({"success": True, "stats": stats})

    except Exception as e:
        logger.error(f"추천 시스템 통계 조회 실패: {e}")
        return Response(
            {"error": f"통계 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def get_collaborative_recommendations(request):
    """협업 필터링 기반 추천"""
    try:
        data = request.data
        user_id = data.get("user_id")
        top_k = data.get("top_k", 5)

        if not user_id:
            return Response(
                {"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        ml_service = MLRecommendationService()
        recommendations = ml_service.get_collaborative_recommendations(
            int(user_id), top_k
        )

        return Response(
            {
                "success": True,
                "recommendations": recommendations,
                "method": "collaborative",
            }
        )

    except Exception as e:
        logger.error(f"협업 필터링 추천 실패: {e}")
        return Response(
            {"error": f"협업 필터링 추천 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def get_content_based_recommendations(request):
    """콘텐츠 기반 필터링 추천"""
    try:
        data = request.data
        user_profile = data.get("user_profile", {})
        top_k = data.get("top_k", 5)

        if not user_profile:
            return Response(
                {"error": "사용자 프로필이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ml_service = MLRecommendationService()
        recommendations = ml_service.get_content_based_recommendations(
            user_profile, top_k
        )

        return Response(
            {
                "success": True,
                "recommendations": recommendations,
                "method": "content_based",
            }
        )

    except Exception as e:
        logger.error(f"콘텐츠 기반 추천 실패: {e}")
        return Response(
            {"error": f"콘텐츠 기반 추천 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def get_hybrid_recommendations(request):
    """하이브리드 추천 (협업 + 콘텐츠)"""
    try:
        data = request.data
        user_id = data.get("user_id")
        user_profile = data.get("user_profile", {})
        top_k = data.get("top_k", 5)

        if not user_id or not user_profile:
            return Response(
                {"error": "사용자 ID와 프로필이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ml_service = MLRecommendationService()
        recommendations = ml_service.get_hybrid_recommendations(
            int(user_id), user_profile, top_k
        )

        return Response(
            {"success": True, "recommendations": recommendations, "method": "hybrid"}
        )

    except Exception as e:
        logger.error(f"하이브리드 추천 실패: {e}")
        return Response(
            {"error": f"하이브리드 추천 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def create_sample_user_data(request):
    """샘플 사용자 데이터 생성 (개발용)"""
    try:
        from django.contrib.auth.models import User
        from users.models import UserProfile
        import numpy as np

        # 기존 샘플 사용자 삭제
        User.objects.filter(username__startswith="sample_user").delete()

        # 샘플 사용자 생성
        sample_users = [
            {
                "username": "sample_user1",
                "age": 25,
                "gender": "M",
                "driving_experience": 3,
                "annual_mileage": 15000,
                "accident_history": 0,
                "selected_insurance": "student",
            },
            {
                "username": "sample_user2",
                "age": 35,
                "gender": "F",
                "driving_experience": 8,
                "annual_mileage": 8000,
                "accident_history": 1,
                "selected_insurance": "premium",
            },
            {
                "username": "sample_user3",
                "age": 45,
                "gender": "M",
                "driving_experience": 15,
                "annual_mileage": 20000,
                "accident_history": 2,
                "selected_insurance": "comprehensive",
            },
            {
                "username": "sample_user4",
                "age": 28,
                "gender": "F",
                "driving_experience": 5,
                "annual_mileage": 12000,
                "accident_history": 0,
                "selected_insurance": "basic",
            },
            {
                "username": "sample_user5",
                "age": 52,
                "gender": "M",
                "driving_experience": 20,
                "annual_mileage": 10000,
                "accident_history": 1,
                "selected_insurance": "senior",
            },
        ]

        created_users = []
        for user_data in sample_users:
            user = User.objects.create_user(
                username=user_data["username"],
                email=f"{user_data['username']}@example.com",
                password="password123",
            )

            profile = UserProfile.objects.create(
                user=user,
                age=user_data["age"],
                gender=user_data["gender"],
                driving_experience=user_data["driving_experience"],
                annual_mileage=user_data["annual_mileage"],
                accident_history=user_data["accident_history"],
                selected_insurance=user_data["selected_insurance"],
                satisfaction_score=np.random.randint(3, 6),
            )

            created_users.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "profile_id": profile.id,
                }
            )

        return Response(
            {
                "success": True,
                "message": f"{len(created_users)}개의 샘플 사용자가 생성되었습니다.",
                "users": created_users,
            }
        )

    except Exception as e:
        logger.error(f"샘플 데이터 생성 실패: {e}")
        return Response(
            {"error": f"샘플 데이터 생성 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_profiles(request):
    """사용자 프로필 목록 조회"""
    try:
        profiles = UserProfile.objects.select_related("user").all()

        profile_list = []
        for profile in profiles:
            profile_list.append(
                {
                    "user_id": profile.user.id,
                    "username": profile.user.username,
                    "age": profile.age,
                    "gender": profile.gender,
                    "driving_experience": profile.driving_experience,
                    "annual_mileage": profile.annual_mileage,
                    "accident_history": profile.accident_history,
                    "selected_insurance": profile.selected_insurance,
                    "satisfaction_score": profile.satisfaction_score,
                }
            )

        return Response(
            {
                "success": True,
                "profiles": profile_list,
                "total_count": len(profile_list),
            }
        )

    except Exception as e:
        logger.error(f"사용자 프로필 조회 실패: {e}")
        return Response(
            {"error": f"프로필 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_model_performance(request):
    """ML 모델 성능 지표 조회"""
    try:
        ml_service = MLRecommendationService()
        performance = ml_service.get_model_performance()

        return Response({"success": True, "performance": performance})

    except Exception as e:
        logger.error(f"모델 성능 조회 실패: {e}")
        return Response(
            {"error": f"모델 성능 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def retrain_ml_models(request):
    """ML 모델 재훈련"""
    try:
        ml_service = MLRecommendationService()
        success = ml_service.retrain_models()

        if success:
            return Response({"success": True, "message": "ML 모델 재훈련이 완료되었습니다."})
        else:
            return Response(
                {"error": "ML 모델 재훈련에 실패했습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"ML 모델 재훈련 실패: {e}")
        return Response(
            {"error": f"ML 모델 재훈련 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_cluster_info(request):
    """사용자 클러스터 정보 조회"""
    try:
        user_id = request.GET.get("user_id")

        if not user_id:
            return Response(
                {"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        ml_service = MLRecommendationService()
        cluster_info = ml_service.get_user_cluster_info(int(user_id))

        return Response({"success": True, "cluster_info": cluster_info})

    except Exception as e:
        logger.error(f"사용자 클러스터 정보 조회 실패: {e}")
        return Response(
            {"error": f"클러스터 정보 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def get_personalized_recommendations(request):
    """개인화된 추천 생성"""
    try:
        data = request.data
        user_id = data.get("user_id")
        user_profile = data.get("user_profile", {})
        recommendation_type = data.get("type", "hybrid")  # collaborative, content, hybrid

        if not user_id:
            return Response(
                {"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        ml_service = MLRecommendationService()

        if recommendation_type == "collaborative":
            recommendations = ml_service.get_collaborative_recommendations(int(user_id), 5)
        elif recommendation_type == "content":
            recommendations = ml_service.get_content_based_recommendations(user_profile, 5)
        else:  # hybrid
            recommendations = ml_service.get_hybrid_recommendations(int(user_id), user_profile, 5)

        return Response({
            "success": True, 
            "recommendations": recommendations,
            "type": recommendation_type
        })

    except Exception as e:
        logger.error(f"개인화 추천 생성 실패: {e}")
        return Response(
            {"error": f"개인화 추천 생성 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def update_user_preference(request):
    """사용자 선호도 업데이트"""
    try:
        data = request.data
        user_id = data.get("user_id")
        selected_product = data.get("selected_product")
        satisfaction_score = data.get("satisfaction_score", 3)

        if not user_id or not selected_product:
            return Response(
                {"error": "사용자 ID와 선택한 상품이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 사용자 프로필 업데이트
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            profile = UserProfile.objects.get(user=user)
            profile.selected_insurance = selected_product
            profile.satisfaction_score = satisfaction_score
            profile.save()

            return Response({
                "success": True, 
                "message": "사용자 선호도가 업데이트되었습니다."
            })

        except UserProfile.DoesNotExist:
            return Response(
                {"error": "사용자 프로필을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

    except Exception as e:
        logger.error(f"사용자 선호도 업데이트 실패: {e}")
        return Response(
            {"error": f"선호도 업데이트 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_recommendation_analytics(request):
    """추천 시스템 분석 데이터"""
    try:
        ml_service = MLRecommendationService()
        
        # 기본 통계
        stats = ml_service.get_recommendation_stats()
        
        # 모델 성능
        performance = ml_service.get_model_performance()
        
        # 사용자 분포
        from users.models import UserProfile
        age_distribution = UserProfile.objects.values('age').annotate(count=Count('id'))
        gender_distribution = UserProfile.objects.values('gender').annotate(count=Count('id'))
        
        analytics = {
            'stats': stats,
            'performance': performance,
            'age_distribution': list(age_distribution),
            'gender_distribution': list(gender_distribution)
        }

        return Response({"success": True, "analytics": analytics})

    except Exception as e:
        logger.error(f"추천 시스템 분석 실패: {e}")
        return Response(
            {"error": f"분석 데이터 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def test_ml_models(request):
    """ML 모델 테스트"""
    try:
        data = request.data
        test_type = data.get("test_type", "all")

        ml_service = MLRecommendationService()

        test_results = {}

        if test_type in ["all", "collaborative"]:
            # 협업 필터링 테스트
            try:
                collaborative_recs = ml_service.get_collaborative_recommendations(1, 3)
                test_results["collaborative"] = {
                    "success": True,
                    "recommendations_count": len(collaborative_recs),
                }
            except Exception as e:
                test_results["collaborative"] = {"success": False, "error": str(e)}

        if test_type in ["all", "content"]:
            # 콘텐츠 기반 필터링 테스트
            try:
                test_profile = {
                    "age": 30,
                    "gender": 0,
                    "driving_experience": 5,
                    "annual_mileage": 12000,
                    "accident_history": 0,
                }
                content_recs = ml_service.get_content_based_recommendations(
                    test_profile, 3
                )
                test_results["content_based"] = {
                    "success": True,
                    "recommendations_count": len(content_recs),
                }
            except Exception as e:
                test_results["content_based"] = {"success": False, "error": str(e)}

        if test_type in ["all", "hybrid"]:
            # 하이브리드 추천 테스트
            try:
                test_profile = {
                    "age": 30,
                    "gender": 0,
                    "driving_experience": 5,
                    "annual_mileage": 12000,
                    "accident_history": 0,
                }
                hybrid_recs = ml_service.get_hybrid_recommendations(1, test_profile, 3)
                test_results["hybrid"] = {
                    "success": True,
                    "recommendations_count": len(hybrid_recs),
                }
            except Exception as e:
                test_results["hybrid"] = {"success": False, "error": str(e)}

        # 모델 성능 테스트
        if test_type in ["all", "performance"]:
            try:
                performance = ml_service.get_model_performance()
                test_results["performance"] = {
                    "success": True,
                    "performance": performance,
                }
            except Exception as e:
                test_results["performance"] = {"success": False, "error": str(e)}

        return Response({"success": True, "test_results": test_results})

    except Exception as e:
        logger.error(f"ML 모델 테스트 실패: {e}")
        return Response(
            {"error": f"ML 모델 테스트 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
