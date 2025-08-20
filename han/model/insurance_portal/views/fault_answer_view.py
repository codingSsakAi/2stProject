# insurance_portal/views/fault_answer_view.py
# 목적: 과실비율 대화형 챗봇 API 엔드포인트
# 동작: POST { "query": "...", "conversation_history": [...] } → 과실비율 분석 결과 반환

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
        ]
    }
    
    Response:
    {
        "result": {
            "needs_more_input": true/false,
            "summary": "재질문 메시지",
            "questions": [{"question": "...", "options": [...]}],
            "final_answer": "최종 답변",
            "table_markdown": "표 데이터",
            "factors": ["가감요소들"],
            "citations": [...]
        }
    }
    """
    try:
        # 지연 import로 순환 import 방지
        from ..services.fault_answerer import answer_fault
        
        # 요청 데이터 파싱
        payload = json.loads(request.body.decode("utf-8"))
        query = (payload.get("query") or "").strip()
        conversation_history = payload.get("conversation_history", [])
        
        # 입력 검증
        if not query:
            return HttpResponseBadRequest("query is required")
        
        # 대화 히스토리 검증 및 정리
        if not isinstance(conversation_history, list):
            conversation_history = []
        
        # 히스토리 항목 검증
        validated_history = []
        for item in conversation_history:
            if isinstance(item, dict) and "role" in item and "content" in item:
                if item["role"] in ["user", "assistant"] and item["content"]:
                    validated_history.append({
                        "role": item["role"],
                        "content": str(item["content"])
                    })
        
        logger.info(f"[FAULT-API] query_len={len(query)} history_len={len(validated_history)}")
        
        # 과실비율 분석 호출
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

