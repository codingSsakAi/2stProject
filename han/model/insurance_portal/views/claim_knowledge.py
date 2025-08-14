# insurance_portal/views/claim_knowledge.py
# 기능: 자동차 사고 보상상식 표시 및 데이터 제공
# - modal_view: 보상상식 모달/페이지 템플릿 반환
# - list_api: merged_cases.json 내용을 반환

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from ..utils.loaders import load_json


def modal_view(request):
    """
    보상상식 모달 또는 단독 페이지를 렌더링합니다.
    - recommendation.html 등에서 {% include "insurance_portal/_claim_knowledge.html" %}로 불릴 수 있습니다.
    - 별도의 URL 접근 시 보상상식 목록 전체를 볼 수 있도록 구성할 수도 있습니다.
    """
    return render(request, "insurance_portal/_claim_knowledge.html")


@csrf_exempt
def list_api(request):
    """
    보상상식 목록 API
    - 데이터 소스: insurance_portal/data/merged_cases.json
    - GET/POST 모두 지원
    응답 예:
    {
        "items": [
            {"title": "사고 유형 1", "description": "..."},
            {"title": "사고 유형 2", "description": "..."},
            ...
        ]
    }
    """
    try:
        items = load_json("merged_cases.json")
    except FileNotFoundError:
        # 데이터 파일이 없는 경우
        return JsonResponse({"items": []})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"items": items})
