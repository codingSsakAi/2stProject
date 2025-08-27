# insurance_portal/views/chatbot.py
# 목적: 사고 과실 챗봇 API 엔드포인트(view)
# 동작: POST { "query": "...질문..." } → Pinecone 검색 결과 반환
# 주의: CSRF 미적용으로 테스트용. 운영 전 CSRF 처리 또는 헤더 적용 필요.

import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# 과실비율 검색 로직(서비스 모듈)
from ..services.pinecone_search_fault import retrieve_fault_ratio

@csrf_exempt
@require_POST
def ask(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        query = (payload.get("query") or "").strip()
        if not query:
            return HttpResponseBadRequest("query is required")

        # Pinecone 검색 호출
        # 기대 반환: [{"score":..., "chunk":..., "file":..., "page":...}, ...]
        matches = retrieve_fault_ratio(query, top_k=5)

        # 직렬화 가능 형태로 반환
        return JsonResponse({"matches": matches}, json_dumps_params={"ensure_ascii": False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)