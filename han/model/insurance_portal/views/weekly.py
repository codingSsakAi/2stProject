# insurance_portal/views/weekly.py
# 기능: 보험상식(주간 정보) 표시 및 데이터 제공
# - weekly_modal_view: UI 템플릿 반환
# - weekly_list_api: weekly_articles.json 내용을 반환

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from ..utils.loaders import load_json


def weekly_modal_view(request):
    """
    보험상식 모달 또는 단독 페이지를 렌더링합니다.
    - recommendation.html 등에서 {% include "insurance_portal/_weekly.html" %}로 불릴 수 있습니다.
    - 별도의 URL로 직접 접근해도 모달/목록이 보이도록 구성할 수 있습니다.
    """
    return render(request, "insurance_portal/_weekly.html")


@csrf_exempt
def weekly_list_api(request):
    """
    보험상식 목록 API
    - 데이터 소스: insurance_portal/data/weekly_articles.json
    - GET/POST 모두 지원
    응답 예:
    {
        "items": [
            {"title": "보험상식 제목1", "content": "내용...", "date": "YYYY-MM-DD"},
            ...
        ]
    }
    """
    try:
        items = load_json("weekly_articles.json")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"items": items})
