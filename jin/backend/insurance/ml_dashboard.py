"""
ML 추천 시스템 대시보드 뷰
머신러닝 기반 보험 추천 시스템 대시보드
"""

import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .ml_service import MLRecommendationService
from users.models import UserProfile

# 로깅 설정
logger = logging.getLogger(__name__)


def ml_dashboard(request):
    """ML 추천 시스템 대시보드"""
    try:
        # ML 서비스 초기화
        ml_service = MLRecommendationService()
        
        # 기본 통계 정보
        stats = ml_service.get_recommendation_stats()
        
        context = {
            'title': 'ML 추천 시스템 대시보드',
            'description': '머신러닝 기반 맞춤형 보험 추천 시스템',
            'stats': stats
        }
        
        return render(request, 'insurance/ml_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"ML 대시보드 로드 실패: {e}")
        return render(request, 'insurance/ml_dashboard.html', {
            'error': f'대시보드 로드 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def ml_dashboard_ajax(request):
    """ML 대시보드 AJAX 요청 처리"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        ml_service = MLRecommendationService()
        
        if action == 'generate_recommendation':
            user_id = data.get('user_id')
            user_profile = data.get('user_profile', {})
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'error': '사용자 ID가 필요합니다.'
                })
            
            recommendations = ml_service.generate_recommendations(user_id, user_profile)
            
            return JsonResponse({
                'success': True,
                'recommendations': recommendations
            })
            
        elif action == 'get_stats':
            stats = ml_service.get_recommendation_stats()
            
            return JsonResponse({
                'success': True,
                'stats': stats
            })
            
        elif action == 'test_models':
            test_type = data.get('test_type', 'all')
            
            test_results = {}
            
            if test_type in ['all', 'collaborative']:
                try:
                    collaborative_recs = ml_service.get_collaborative_recommendations(1, 3)
                    test_results['collaborative'] = {
                        'success': True,
                        'recommendations_count': len(collaborative_recs)
                    }
                except Exception as e:
                    test_results['collaborative'] = {
                        'success': False,
                        'error': str(e)
                    }
            
            if test_type in ['all', 'content']:
                try:
                    test_profile = {
                        'age': 30, 
                        'gender': 0, 
                        'driving_experience': 5, 
                        'annual_mileage': 12000, 
                        'accident_history': 0
                    }
                    content_recs = ml_service.get_content_based_recommendations(test_profile, 3)
                    test_results['content_based'] = {
                        'success': True,
                        'recommendations_count': len(content_recs)
                    }
                except Exception as e:
                    test_results['content_based'] = {
                        'success': False,
                        'error': str(e)
                    }
            
            if test_type in ['all', 'hybrid']:
                try:
                    test_profile = {
                        'age': 30, 
                        'gender': 0, 
                        'driving_experience': 5, 
                        'annual_mileage': 12000, 
                        'accident_history': 0
                    }
                    hybrid_recs = ml_service.get_hybrid_recommendations(1, test_profile, 3)
                    test_results['hybrid'] = {
                        'success': True,
                        'recommendations_count': len(hybrid_recs)
                    }
                except Exception as e:
                    test_results['hybrid'] = {
                        'success': False,
                        'error': str(e)
                    }
            
            return JsonResponse({
                'success': True,
                'test_results': test_results
            })
            
        else:
            return JsonResponse({
                'success': False,
                'error': '지원하지 않는 액션입니다.'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        })
    except Exception as e:
        logger.error(f"ML 대시보드 AJAX 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'처리 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["GET"])
def ml_dashboard_stats_ajax(request):
    """ML 대시보드 통계 AJAX 요청 처리"""
    try:
        ml_service = MLRecommendationService()
        stats = ml_service.get_recommendation_stats()
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"ML 대시보드 통계 AJAX 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'통계 조회 중 오류가 발생했습니다: {str(e)}'
        }) 