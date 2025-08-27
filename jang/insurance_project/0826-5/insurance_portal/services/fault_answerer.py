# insurance_portal/views/fault_answer_view.py
# 목적: 과실비율 대화형 챗봇 + 네비게이션 API 엔드포인트
# 수정: 네비게이션 데이터 제공 엔드포인트 추가

import json
import logging
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def fault_answer(request):
    """
    과실비율 대화형 챗봇 API
    
    Request:
    {
        "query": "교차로에서 사고가 났어요",
        "conversation_history": [
            {"role": "user", "content": "이전 질문"},
            {"role": "assistant", "content": "이전 답변"}
        ],
        "navigation_context": {
            "path": ["교차로 사고", "신호등 교차로"],
            "selected_option": "직진차 신호준수 - 좌회전차 신호위반",
            "is_navigation_query": true
        },
        "is_text_mode": false
    }
    
    Response:
    {
        "result": {
            "needs_more_input": true/false,
            "summary": "재질문 메시지",
            "questions": [{"question": "...", "options": [...]}],
            
            // 최종 결과 (네비게이션 완료 시)
            "accident_description": "사고 설명",
            "base_fault": "70:30",
            "base_fault_description": "기본 과실비율 설명",
            "modification_factors": "수정 요소들",
            "modification_description": "수정 요소 설명",
            "final_fault": "75:25",
            "legal_info": "관련 법규",
            "precedents": "관련 판례",
            "citations": [...]
        }
    }
    """
    try:
        # 지연 import로 순환 import 방지
        from ..services.fault_answerer import answer_fault
        from ..services.navigation_fault_processor import process_navigation_query
        
        # 요청 데이터 파싱
        payload = json.loads(request.body.decode("utf-8"))
        query = (payload.get("query") or "").strip()
        conversation_history = payload.get("conversation_history", [])
        navigation_context = payload.get("navigation_context", {})
        is_text_mode = payload.get("is_text_mode", False)
        
        # 입력 검증
        if not query:
            return HttpResponseBadRequest("query is required")
        
        # 대화 히스토리 검증 및 정리
        if not isinstance(conversation_history, list):
            conversation_history = []
        
        validated_history = []
        for item in conversation_history:
            if isinstance(item, dict) and "role" in item and "content" in item:
                if item["role"] in ["user", "assistant"] and item["content"]:
                    validated_history.append({
                        "role": item["role"],
                        "content": str(item["content"])
                    })
        
        logger.info(f"[FAULT-API] query_len={len(query)} history_len={len(validated_history)} nav_mode={bool(navigation_context.get('is_navigation_query'))}")
        
        # 네비게이션 쿼리인 경우 특별 처리
        if navigation_context.get('is_navigation_query'):
            result = process_navigation_query(
                query=query,
                navigation_context=navigation_context
            )
        else:
            # 기존 대화형 처리
            result = answer_fault(
                query=query, 
                conversation_history=validated_history
            )
        
        logger.info(f"[FAULT-API] result needs_more_input={result.get('needs_more_input')}")
        
        # 성공 응답
        return JsonResponse({
            "result": result
        }, json_dumps_params={"ensure_ascii": False})
        
    except ImportError as e:
        logger.error(f"[FAULT-API] Import error: {e}")
        return JsonResponse({
            "error": "Service module not available"
        }, status=500)
        
    except json.JSONDecodeError as e:
        logger.error(f"[FAULT-API] JSON decode error: {e}")
        return JsonResponse({
            "error": "Invalid JSON format"
        }, status=400)
        
    except Exception as e:
        logger.exception(f"[FAULT-API] Unexpected error: {e}")
        return JsonResponse({
            "error": "Internal server error occurred"
        }, status=500)


@csrf_exempt
@require_POST
def navigation_data(request):
    """
    네비게이션 데이터 제공 API
    
    Request:
    {
        "path": ["교차로 사고", "신호등 교차로"]  // 현재 경로 (null이면 최상위)
    }
    
    Response:
    {
        "result": {
            "level": 1,
            "path": ["교차로 사고"],
            "title": "교차로 사고 세부 유형을 선택해주세요",
            "is_final": false,
            "items": [
                {
                    "key": "신호등 교차로",
                    "title": "신호등 교차로", 
                    "icon": "fas fa-traffic-light",
                    "description": "신호등이 설치된 교차로에서의 사고"
                }
            ],
            "options": null  // is_final=true인 경우에만 존재
        }
    }
    """
    try:
        # 네비게이션 데이터 관리자 import
        from ..services.navigation_data import get_navigation_data
        
        # 요청 데이터 파싱
        payload = json.loads(request.body.decode("utf-8"))
        path = payload.get("path", None)
        
        # path가 빈 리스트인 경우 None으로 처리
        if path is not None and len(path) == 0:
            path = None
        
        # path 유효성 검사
        if path is not None:
            if not isinstance(path, list):
                return HttpResponseBadRequest("path must be a list")
            
            # 각 경로 항목이 문자열인지 확인
            for item in path:
                if not isinstance(item, str):
                    return HttpResponseBadRequest("path items must be strings")
        
        logger.info(f"[NAV-API] Request path: {path}")
        
        # 네비게이션 데이터 조회
        result = get_navigation_data(path)
        
        if not result:
            return JsonResponse({
                "error": "Navigation data not found"
            }, status=404)
        
        logger.info(f"[NAV-API] Response level: {result.get('level')}, items: {len(result.get('items', []))}")
        
        # 성공 응답
        return JsonResponse({
            "result": result
        }, json_dumps_params={"ensure_ascii": False})
        
    except ImportError as e:
        logger.error(f"[NAV-API] Import error: {e}")
        return JsonResponse({
            "error": "Navigation service not available"
        }, status=500)
        
    except json.JSONDecodeError as e:
        logger.error(f"[NAV-API] JSON decode error: {e}")
        return JsonResponse({
            "error": "Invalid JSON format"
        }, status=400)
        
    except Exception as e:
        logger.exception(f"[NAV-API] Unexpected error: {e}")
        return JsonResponse({
            "error": "Internal server error occurred"
        }, status=500)


# 기존 ask 함수는 호환성을 위해 유지
@csrf_exempt
@require_POST
def ask(request):
    """
    기존 호환성을 위한 간단한 검색 API (기존 chatbot.py 내용)
    """
    try:
        from ..services.pinecone_search_fault import retrieve_fault_ratio
        
        payload = json.loads(request.body.decode("utf-8"))
        query = (payload.get("query") or "").strip()
        if not query:
            return HttpResponseBadRequest("query is required")

        # Pinecone 검색 호출
        matches = retrieve_fault_ratio(query, top_k=5)

        # 직렬화 가능 형태로 반환
        return JsonResponse({"matches": matches}, json_dumps_params={"ensure_ascii": False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)