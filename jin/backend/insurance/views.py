"""
RAG 시스템 API 뷰
문서 검색, 응답 생성, 관리 기능을 제공합니다.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import logging

from .services import rag_service
from .models import PolicyDocument, InsuranceCompany

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def search_documents_api(request):
    """문서 검색 API"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        company_filter = data.get('company_filter', None)
        top_k = data.get('top_k', 10)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': '검색어를 입력해주세요.'
            })
        
        # 문서 검색
        results = rag_service.search_documents(
            query=query,
            company_filter=company_filter,
            top_k=top_k
        )
        
        return JsonResponse({
            'success': True,
            'results': results,
            'query': query,
            'total_results': len(results)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        })
    except Exception as e:
        logger.error(f"문서 검색 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'검색 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def generate_response_api(request):
    """RAG 응답 생성 API"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        context_docs = data.get('context_docs', [])
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': '질문을 입력해주세요.'
            })
        
        # 응답 생성
        response = rag_service.generate_response(query, context_docs)
        
        return JsonResponse({
            'success': True,
            'response': response,
            'query': query
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        })
    except Exception as e:
        logger.error(f"응답 생성 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'응답 생성 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """통합 채팅 API (검색 + 응답 생성)"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        company_filter = data.get('company_filter', None)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': '질문을 입력해주세요.'
            })
        
        # 1단계: 관련 문서 검색
        search_results = rag_service.search_documents(
            query=query,
            company_filter=company_filter,
            top_k=5
        )
        
        if not search_results:
            return JsonResponse({
                'success': False,
                'error': '관련 문서를 찾을 수 없습니다.'
            })
        
        # 2단계: 응답 생성
        response = rag_service.generate_response(query, search_results)
        
        return JsonResponse({
            'success': True,
            'response': response,
            'query': query,
            'context_docs': search_results,
            'total_context_docs': len(search_results)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        })
    except Exception as e:
        logger.error(f"채팅 API 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'처리 중 오류가 발생했습니다: {str(e)}'
        })


@login_required
def rag_dashboard(request):
    """RAG 대시보드"""
    try:
        # 인덱스 통계
        stats = rag_service.get_index_stats()
        
        # 보험사 목록
        companies = InsuranceCompany.objects.filter(is_active=True)
        
        # 최근 업로드된 문서
        recent_documents = PolicyDocument.objects.filter(
            is_active=True
        ).order_by('-upload_date')[:10]
        
        context = {
            'stats': stats,
            'companies': companies,
            'recent_documents': recent_documents,
            'total_documents': PolicyDocument.objects.filter(is_active=True).count(),
            'total_companies': companies.count(),
        }
        
        return render(request, 'insurance/rag_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"RAG 대시보드 오류: {e}")
        return render(request, 'insurance/rag_dashboard.html', {
            'error': f'대시보드 로딩 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["GET"])
def get_index_stats_api(request):
    """인덱스 통계 API"""
    try:
        stats = rag_service.get_index_stats()
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"인덱스 통계 조회 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'통계 조회 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def upload_document_api(request):
    """문서 업로드 API"""
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        
        if not document_id:
            return JsonResponse({
                'success': False,
                'error': '문서 ID가 필요합니다.'
            })
        
        try:
            document = PolicyDocument.objects.get(id=document_id)
        except PolicyDocument.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '문서를 찾을 수 없습니다.'
            })
        
        # Pinecone에 업로드
        success = rag_service.upload_document(document)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'문서가 성공적으로 업로드되었습니다: {document.get_file_name()}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'문서 업로드에 실패했습니다: {document.get_file_name()}'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        })
    except Exception as e:
        logger.error(f"문서 업로드 API 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'업로드 중 오류가 발생했습니다: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def delete_document_api(request):
    """문서 삭제 API"""
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        
        if not document_id:
            return JsonResponse({
                'success': False,
                'error': '문서 ID가 필요합니다.'
            })
        
        try:
            document = PolicyDocument.objects.get(id=document_id)
        except PolicyDocument.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '문서를 찾을 수 없습니다.'
            })
        
        # Pinecone에서 삭제
        success = rag_service.delete_document(document)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'문서가 성공적으로 삭제되었습니다: {document.get_file_name()}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'문서 삭제에 실패했습니다: {document.get_file_name()}'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        })
    except Exception as e:
        logger.error(f"문서 삭제 API 오류: {e}")
        return JsonResponse({
            'success': False,
            'error': f'삭제 중 오류가 발생했습니다: {str(e)}'
        })
