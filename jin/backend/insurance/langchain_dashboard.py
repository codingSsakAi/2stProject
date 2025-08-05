"""
LangChain 대시보드
LangChain + LLM 서비스를 테스트할 수 있는 웹 인터페이스
"""

import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json

from .langchain_service import LangChainService

# 로깅 설정
logger = logging.getLogger(__name__)


def langchain_dashboard(request):
    """LangChain 대시보드 메인 페이지"""
    try:
        # 서비스 상태 확인
        langchain_service = LangChainService()
        status_info = langchain_service.get_service_status()

        context = {
            "title": "LangChain + LLM 대시보드",
            "status_info": status_info,
            "available_tools": [
                "보험_문서_검색",
                "보험_회사_정보_조회",
                "보험_추천_생성",
                "보험_비교_분석",
            ],
        }

        return render(request, "insurance/langchain_dashboard.jinja.html", context)

    except Exception as e:
        logger.error(f"LangChain 대시보드 로드 실패: {e}")
        return render(
            request,
            "insurance/langchain_dashboard.jinja.html",
            {
                "title": "LangChain + LLM 대시보드",
                "error": f"대시보드 로드 중 오류가 발생했습니다: {str(e)}",
            },
        )


@csrf_exempt
def langchain_chat_ajax(request):
    """LangChain 채팅 AJAX 처리"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "").strip()

            if not user_message:
                return JsonResponse(
                    {"success": False, "error": "메시지가 비어있습니다."}
                )

            # LangChain 서비스로 채팅
            langchain_service = LangChainService()
            response = langchain_service.chat_with_agent(user_message)

            return JsonResponse(
                {"success": True, "response": response, "user_message": user_message}
            )

        except Exception as e:
            logger.error(f"LangChain 채팅 AJAX 실패: {e}")
            return JsonResponse(
                {"success": False, "error": f"채팅 중 오류가 발생했습니다: {str(e)}"}
            )

    return JsonResponse({"success": False, "error": "POST 요청만 지원합니다."})


@csrf_exempt
def langchain_tool_test_ajax(request):
    """LangChain 도구 테스트 AJAX 처리"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            tool_name = data.get("tool_name", "").strip()
            tool_input = data.get("tool_input", "").strip()

            if not tool_name or not tool_input:
                return JsonResponse(
                    {"success": False, "error": "도구명과 입력값이 필요합니다."}
                )

            # LangChain 서비스로 도구 테스트
            langchain_service = LangChainService()

            tool_functions = {
                "보험_문서_검색": langchain_service._search_insurance_documents,
                "보험_회사_정보_조회": langchain_service._get_insurance_company_info,
                "보험_추천_생성": langchain_service._generate_insurance_recommendation,
                "보험_비교_분석": langchain_service._compare_insurance_products,
            }

            if tool_name not in tool_functions:
                return JsonResponse(
                    {"success": False, "error": f"알 수 없는 도구명: {tool_name}"}
                )

            result = tool_functions[tool_name](tool_input)

            return JsonResponse(
                {
                    "success": True,
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "result": result,
                }
            )

        except Exception as e:
            logger.error(f"LangChain 도구 테스트 AJAX 실패: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"도구 테스트 중 오류가 발생했습니다: {str(e)}",
                }
            )

    return JsonResponse({"success": False, "error": "POST 요청만 지원합니다."})


@csrf_exempt
def langchain_memory_ajax(request):
    """LangChain 메모리 관리 AJAX 처리"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action", "").strip()

            langchain_service = LangChainService()

            if action == "get_history":
                history = langchain_service.get_conversation_history()
                return JsonResponse({"success": True, "history": history})

            elif action == "clear_memory":
                langchain_service.clear_memory()
                return JsonResponse(
                    {"success": True, "message": "대화 메모리가 초기화되었습니다."}
                )

            else:
                return JsonResponse(
                    {"success": False, "error": f"알 수 없는 액션: {action}"}
                )

        except Exception as e:
            logger.error(f"LangChain 메모리 AJAX 실패: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"메모리 관리 중 오류가 발생했습니다: {str(e)}",
                }
            )

    return JsonResponse({"success": False, "error": "POST 요청만 지원합니다."})


@csrf_exempt
def langchain_status_ajax(request):
    """LangChain 서비스 상태 AJAX 처리"""
    if request.method == "GET":
        try:
            langchain_service = LangChainService()
            status_info = langchain_service.get_service_status()

            return JsonResponse({"success": True, "status": status_info})

        except Exception as e:
            logger.error(f"LangChain 상태 AJAX 실패: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"상태 조회 중 오류가 발생했습니다: {str(e)}",
                }
            )

    return JsonResponse({"success": False, "error": "GET 요청만 지원합니다."})
