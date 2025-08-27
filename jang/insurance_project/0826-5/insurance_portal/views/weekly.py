# insurance_portal/views/weekly.py
# 목적: 보험 상식(weekly) 페이지 및 partial 렌더
# 데이터 로드: staticfiles의 weekly_articles.json을 파일시스템에서 찾아 로드

import json
from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.contrib.staticfiles import finders

# 정적 JSON 경로(앱 내부 static 경로 기준)
WEEKLY_JSON_STATIC_PATH = "insurance_portal/json/weekly_articles.json"

def _load_weekly_articles():
    """
    staticfiles finders로 실제 파일 경로를 찾아 JSON 로드
    개발/운영(STATIC_ROOT 수집) 모두 대응
    """
    path = finders.find(WEEKLY_JSON_STATIC_PATH)
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def page(request):
    """
    메인 페이지 렌더(템플릿에서 JS로 partial 불러오거나,
    서버사이드로 바로 articles를 주입하는 방식 둘 다 가능)
    여기서는 UI 구조만 제공하고 데이터는 partial에서 주입
    """
    return render(request, "insurance_portal/weekly.html")

def partial(request):
    """
    부분 렌더: weekly_partial.html에 articles 컨텍스트로 주입
    프런트(JS)가 /weekly/partial/을 호출해서 본문만 갱신하는 용도
    """
    data = _load_weekly_articles()
    if data is None:
        return HttpResponseNotFound("weekly_articles.json not found")
    return render(request, "insurance_portal/weekly_partial.html", {"articles": data})
