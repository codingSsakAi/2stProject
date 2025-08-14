# insurance_portal/views/guide.py
# 기능: 사고 처리 가이드 표시 및 데이터 제공
# - modal_view: 가이드 모달/페이지 템플릿 반환
# - steps_api: 사고처리.json / 증거확보.json / 다양한처리.json 통합 반환

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from ..utils.loaders import load_json


def modal_view(request):
    """사고 처리 가이드 모달 또는 단독 페이지 렌더링"""
    return render(request, "insurance_portal/_guide.html")


@csrf_exempt
def steps_api(request):
    """
    가이드 데이터 API
    - basic:   insurance_portal/data/사고처리.json  (기본 6단계)
    - evidence:insurance_portal/data/증거확보.json  (증거 확보 팁)
    - various: insurance_portal/data/다양한처리.json (경찰서/보험회사/피해물/피해자 흐름)
    """

    # 1) 기본값(예외 시에도 항상 반환 가능)
    various = {
        "섹션": [],
        "보험회사": {"절차": []},
        "피해물": {"절차": []},
        "피해자": {"절차": []},
    }
    basic_steps = []
    evidence = {"title": "증거 확보", "items": []}

    # 2) 파일 로드(있으면 덮어쓰기)
    try:
        loaded = load_json("다양한처리.json")
        if isinstance(loaded, dict):
            various = loaded
    except Exception:
        pass  # 기본값 유지

    try:
        loaded = load_json("사고처리.json")
        if isinstance(loaded, list):
            basic_steps = loaded
    except Exception:
        pass  # 기본값 유지

    try:
        loaded = load_json("증거확보.json")
        if isinstance(loaded, dict):
            evidence = loaded
    except Exception:
        pass  # 기본값 유지

    # 3) 항상 정의된 값으로 반환
    return JsonResponse({
        "various": various,
        "basic": basic_steps,
        "evidence": evidence,
    })
