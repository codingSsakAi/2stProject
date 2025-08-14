import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json
from .models import InsuranceDocument, DocumentChunk, InsuranceCompany
from .forms import DocumentUploadForm
from .utils import PDFProcessor
from .services import DocumentEmbeddingService
from datetime import datetime
from .models import ChatSession, ChatHistory
from django.utils import timezone
from .decorators import admin_required, user_required, chatbot_access_required
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

# Create your views here.


@chatbot_access_required
def chat_view(request):
    """RAG 챗봇 상담 뷰 (실시간 채팅)"""

    # 채팅 세션 목록 조회
    chat_sessions = ChatSession.objects.filter(user=request.user).order_by(
        "-updated_at"
    )

    # 최근 세션 (가장 최근에 업데이트된 세션)
    latest_session = chat_sessions.first()

    # 최근 세션의 채팅 기록 (시간 순서)
    latest_chat_history = []
    if latest_session:
        latest_chat_history = ChatHistory.objects.filter(
            session=latest_session
        ).order_by(
            "created_at"
        )  # 시간 순서대로

        # 메타데이터의 시간 포맷 처리
        for message in latest_chat_history:
            if message.metadata:
                try:
                    # generated_at이 있는 경우 포맷팅
                    if "generated_at" in message.metadata:
                        generated_at = message.metadata["generated_at"]
                        if isinstance(generated_at, str):
                            # T를 공백으로 변경하고 초 단위까지만 표시
                            formatted_time = generated_at[:19].replace("T", " ")
                            message.metadata["formatted_time"] = formatted_time
                        else:
                            message.metadata["formatted_time"] = "시간 정보 없음"
                    else:
                        # generated_at이 없는 경우 기본값 설정
                        message.metadata["formatted_time"] = "시간 정보 없음"
                        message.metadata["generated_at"] = None
                except Exception as e:
                    # 메타데이터가 None이거나 처리 중 오류 발생 시 기본값 설정
                    if message.metadata is None:
                        message.metadata = {}
                    message.metadata["formatted_time"] = "시간 정보 없음"
                    message.metadata["generated_at"] = None

    context = {
        "title": "챗봇 상담",
        "chat_sessions": chat_sessions,
        "latest_session": latest_session,
        "latest_chat_history": latest_chat_history,
    }

    return render(request, "chatbot/chat.jinja.html", context)


@chatbot_access_required
@require_http_methods(["POST"])
def api_send_message(request):
    """실시간 채팅을 위한 AJAX API - 메시지 전송 및 답변 생성"""
    try:
        # JSON 데이터 파싱
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse(
                {"success": False, "error": "메시지를 입력해주세요."}, status=400
            )

        # RAG 챗봇 서비스로 답변 생성
        from .services import RAGChatbotService

        chatbot_service = RAGChatbotService()

        # 사용자 메시지로 관련 문서 검색
        relevant_chunks = chatbot_service.search_relevant_documents(user_message)

        # OpenAI API로 답변 생성 (사용자 정보 전달)
        response = chatbot_service.generate_response(
            user_message, relevant_chunks, request.user
        )

        # 채팅 기록 저장
        chat_session = ChatSession.objects.filter(user=request.user).first()
        if not chat_session:
            chat_session = ChatSession.objects.create(
                user=request.user, title=user_message[:50] + "..."
            )

        # 사용자 메시지 저장
        user_chat_history = ChatHistory.objects.create(
            user=request.user,
            session=chat_session,
            message=user_message,
            is_user=True,
        )

        # 챗봇 답변 저장
        bot_answer = response["answer"]
        bot_chat_history = ChatHistory.objects.create(
            user=request.user,
            session=chat_session,
            message=bot_answer,
            is_user=False,
            metadata=response.get("metadata", {}),
        )

        # 세션 업데이트
        chat_session.updated_at = timezone.now()
        chat_session.save()

        # 응답 데이터 구성
        response_data = {
            "success": True,
            "user_message": {
                "id": user_chat_history.id,
                "message": user_message,
                "created_at": user_chat_history.created_at.isoformat(),
                "is_user": True,
            },
            "bot_message": {
                "id": bot_chat_history.id,
                "message": bot_answer,
                "created_at": bot_chat_history.created_at.isoformat(),
                "is_user": False,
                "metadata": response.get("metadata", {}),
            },
        }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "잘못된 JSON 형식입니다."}, status=400
        )
    except Exception as e:
        logger.error(f"API 메시지 전송 오류: {e}")
        return JsonResponse(
            {"success": False, "error": f"서버 오류가 발생했습니다: {str(e)}"},
            status=500,
        )


@chatbot_access_required
@require_http_methods(["POST"])
def api_insurance_profile(request):
    """보험 추천을 위한 프로필 정보 입력 API"""
    try:
        data = json.loads(request.body)

        # 사용자 프로필 업데이트 또는 생성
        profile, created = UserProfile.objects.get_or_create(user=request.user)

        # 입력받은 데이터로 프로필 업데이트
        if "birth_date" in data:
            profile.birth_date = data["birth_date"]
        if "gender" in data:
            profile.gender = data["gender"]
        if "residence_area" in data:
            profile.residence_area = data["residence_area"]
        if "driving_experience" in data:
            profile.driving_experience = data["driving_experience"]
        if "car_type" in data:
            profile.car_type = data["car_type"]
        if "annual_mileage" in data:
            profile.annual_mileage = data["annual_mileage"]
        if "accident_history" in data:
            profile.accident_history = data["accident_history"]
        if "coverage_level" in data:
            profile.coverage_level = data["coverage_level"]
        if "additional_coverage_interest" in data:
            profile.additional_coverage_interest = data["additional_coverage_interest"]

        profile.save()

        # 보험 추천 계산
        from .insurance_service import InsuranceRecommendationService

        insurance_service = InsuranceRecommendationService()
        result = insurance_service.calculate_insurance_recommendations(
            request.user, "chatbot"
        )

        return JsonResponse(
            {
                "success": True,
                "message": "프로필 정보가 저장되었습니다.",
                "recommendation": result,
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": f"프로필 저장 중 오류가 발생했습니다: {str(e)}",
            },
            status=500,
        )


@chatbot_access_required
@require_http_methods(["GET"])
def api_get_insurance_profile(request):
    """현재 사용자의 보험 추천 프로필 정보 조회"""
    try:
        profile = getattr(request.user, "profile", None)

        if not profile:
            return JsonResponse(
                {"success": True, "has_profile": False, "profile": None}
            )

        profile_data = {
            "birth_date": (
                profile.birth_date.strftime("%Y-%m-%d") if profile.birth_date else None
            ),
            "gender": profile.gender,
            "residence_area": profile.residence_area,
            "driving_experience": profile.driving_experience,
            "car_type": profile.car_type,
            "annual_mileage": profile.annual_mileage,
            "accident_history": profile.accident_history,
            "coverage_level": profile.coverage_level,
            "additional_coverage_interest": profile.additional_coverage_interest,
        }

        return JsonResponse(
            {"success": True, "has_profile": True, "profile": profile_data}
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": f"프로필 조회 중 오류가 발생했습니다: {str(e)}",
            },
            status=500,
        )


@chatbot_access_required
def chat_session_view(request, session_id):
    """특정 채팅 세션 상세 보기"""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    chat_history = chat_session.chat_history.all().order_by("created_at")

    # 메타데이터의 시간 포맷 처리
    for message in chat_history:
        if message.metadata:
            try:
                # generated_at이 있는 경우 포맷팅
                if "generated_at" in message.metadata:
                    generated_at = message.metadata["generated_at"]
                    if isinstance(generated_at, str):
                        # T를 공백으로 변경하고 초 단위까지만 표시
                        formatted_time = generated_at[:19].replace("T", " ")
                        message.metadata["formatted_time"] = formatted_time
                    else:
                        message.metadata["formatted_time"] = "시간 정보 없음"
                else:
                    # generated_at이 없는 경우 기본값 설정
                    message.metadata["formatted_time"] = "시간 정보 없음"
                    message.metadata["generated_at"] = None
            except Exception as e:
                # 메타데이터가 None이거나 처리 중 오류 발생 시 기본값 설정
                if message.metadata is None:
                    message.metadata = {}
                message.metadata["formatted_time"] = "시간 정보 없음"
                message.metadata["generated_at"] = None

    context = {
        "title": f"채팅 세션 - {chat_session.title}",
        "chat_session": chat_session,
        "chat_history": chat_history,
    }

    return render(request, "chatbot/chat_session.jinja.html", context)


@chatbot_access_required
def chat_delete_view(request, session_id):
    """채팅 세션 삭제"""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    if request.method == "POST":
        try:
            chat_session.delete()
            messages.success(request, "채팅 세션이 삭제되었습니다.")
        except Exception as e:
            messages.error(request, f"채팅 세션 삭제 중 오류가 발생했습니다: {str(e)}")

        return redirect("chatbot:chat")

    context = {
        "title": "채팅 세션 삭제 확인",
        "chat_session": chat_session,
    }

    return render(request, "chatbot/chat_delete_confirm.jinja.html", context)



@admin_required
def document_upload_view(request):
    """PDF 문서 업로드 뷰"""
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 폼에서 데이터 가져오기
                title = form.cleaned_data["title"]
                insurance_company = form.cleaned_data["insurance_company"]
                pdf_file = form.cleaned_data["pdf_file"]

                # PDF 처리기 초기화
                pdf_processor = PDFProcessor()

                # 문서 모델에 저장
                document = form.save(commit=False)
                document.uploaded_by = request.user
                document.status = "uploaded"
                document.save()

                # PDF 파일 경로
                pdf_path = document.pdf_file.path

                # 텍스트 추출 및 처리
                text = pdf_processor.process_pdf_with_ocr(pdf_path)
                if text:
                    cleaned_text = pdf_processor.clean_text(text)

                    # 텍스트 파일로 저장 (모델의 upload_to 함수 사용)
                    txt_filename = (
                        f"{os.path.splitext(os.path.basename(pdf_file.name))[0]}.txt"
                    )
                    txt_path = os.path.join(
                        "media",
                        "documents",
                        "txt",
                        insurance_company.name,
                        txt_filename,
                    )
                    os.makedirs(os.path.dirname(txt_path), exist_ok=True)

                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(cleaned_text)

                    # 문서 모델 업데이트
                    document.txt_file = (
                        f"documents/txt/{insurance_company.name}/{txt_filename}"
                    )
                    document.status = "completed"
                    document.processed_at = datetime.now()
                    document.save()

                    # 텍스트 청크 생성
                    chunks = pdf_processor.split_text_into_chunks(cleaned_text)
                    chunk_objects = []
                    for i, chunk_text in enumerate(chunks):
                        chunk_obj = DocumentChunk.objects.create(
                            document=document, chunk_text=chunk_text, chunk_index=i
                        )
                        chunk_objects.append(chunk_obj)

                    # Embedding 처리 및 Pinecone 업로드
                    try:
                        embedding_service = DocumentEmbeddingService()

                        # 청크 데이터 준비
                        chunk_data = []
                        for chunk_obj in chunk_objects:
                            chunk_data.append(
                                {
                                    "id": chunk_obj.id,
                                    "document_id": document.id,
                                    "chunk_index": chunk_obj.chunk_index,
                                    "content": chunk_obj.chunk_text,
                                    "insurance_company": insurance_company.name,
                                    "document_title": document.title,
                                    "created_at": (
                                        chunk_obj.created_at.isoformat()
                                        if chunk_obj.created_at
                                        else ""
                                    ),
                                }
                            )

                        # Embedding 처리 및 Pinecone 업로드
                        if chunk_data:
                            success = embedding_service.process_document_chunks(
                                chunk_data
                            )
                            if success:
                                messages.success(
                                    request,
                                    f"문서가 성공적으로 처리되었습니다. (Embedding 완료)",
                                )
                            else:
                                messages.warning(
                                    request,
                                    f"문서는 처리되었지만 Embedding 처리에 실패했습니다.",
                                )
                        else:
                            messages.success(
                                request, f"문서가 성공적으로 처리되었습니다."
                            )

                    except Exception as e:
                        messages.warning(
                            request,
                            f"문서는 처리되었지만 Embedding 처리 중 오류가 발생했습니다: {str(e)}",
                        )
                else:
                    document.status = "error"
                    document.error_message = "텍스트 추출에 실패했습니다."
                    document.save()
                    messages.error(request, "텍스트 추출에 실패했습니다.")
            except Exception as e:
                messages.error(request, f"파일 처리 중 오류가 발생했습니다: {str(e)}")

            return redirect("chatbot:document_list")
    else:
        form = DocumentUploadForm()

    return render(
        request,
        "chatbot/document_upload.jinja.html",
        {"title": "PDF 문서 업로드", "form": form},
    )


@admin_required
def document_list_view(request):
    """업로드된 문서 목록 뷰"""
    documents = InsuranceDocument.objects.filter(uploaded_by=request.user).order_by(
        "-uploaded_at"
    )

    return render(
        request,
        "chatbot/document_list.jinja.html",
        {"title": "문서 목록", "documents": documents},
    )


@admin_required
def document_detail_view(request, document_id):
    """문서 상세 보기 뷰"""
    document = get_object_or_404(
        InsuranceDocument, id=document_id, uploaded_by=request.user
    )
    chunks = document.chunks.all().order_by("chunk_index")

    return render(
        request,
        "chatbot/document_detail.jinja.html",
        {
            "title": f"문서 상세 - {document.title}",
            "document": document,
            "chunks": chunks,
        },
    )


@admin_required
def document_delete_view(request, document_id):
    """문서 삭제 뷰"""
    document = get_object_or_404(
        InsuranceDocument, id=document_id, uploaded_by=request.user
    )

    if request.method == "POST":
        try:
            # Pinecone에서 벡터 삭제
            try:
                embedding_service = DocumentEmbeddingService()
                embedding_service.delete_document_vectors(document.id)
            except Exception as e:
                # 벡터 삭제 실패해도 문서 삭제는 계속 진행
                pass

            # 파일 삭제
            if document.pdf_file:
                if os.path.exists(document.pdf_file.path):
                    os.remove(document.pdf_file.path)

            if document.txt_file:
                if os.path.exists(document.txt_file.path):
                    os.remove(document.txt_file.path)

            # 모델 삭제
            document.delete()
            messages.success(request, "문서가 성공적으로 삭제되었습니다.")

        except Exception as e:
            messages.error(request, f"문서 삭제 중 오류가 발생했습니다: {str(e)}")

        return redirect("chatbot:document_list")

    return render(
        request,
        "chatbot/document_delete_confirm.jinja.html",
        {"title": "문서 삭제 확인", "document": document},
    )


@admin_required
def document_process_view(request, document_id):
    """문서 재처리 뷰"""
    document = get_object_or_404(
        InsuranceDocument, id=document_id, uploaded_by=request.user
    )

    if request.method == "POST":
        try:
            # 기존 청크 삭제
            document.chunks.all().delete()

            # PDF 처리기로 재처리
            pdf_processor = PDFProcessor()

            if document.txt_file and os.path.exists(document.txt_file.path):
                with open(document.txt_file.path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                text = pdf_processor.process_pdf_with_ocr(document.pdf_file.path)
                if text:
                    cleaned_text = pdf_processor.clean_text(text)

                    # 텍스트 파일 업데이트
                    with open(document.txt_file.path, "w", encoding="utf-8") as f:
                        f.write(cleaned_text)
                    text = cleaned_text

            if text:
                # 텍스트 청크 재생성
                chunks = pdf_processor.split_text_into_chunks(text)
                chunk_objects = []
                for i, chunk_text in enumerate(chunks):
                    chunk_obj = DocumentChunk.objects.create(
                        document=document, chunk_text=chunk_text, chunk_index=i
                    )
                    chunk_objects.append(chunk_obj)

                # Embedding 재처리 및 Pinecone 업로드
                try:
                    embedding_service = DocumentEmbeddingService()

                    # 기존 벡터 삭제
                    embedding_service.delete_document_vectors(document.id)

                    # 청크 데이터 준비
                    chunk_data = []
                    for chunk_obj in chunk_objects:
                        chunk_data.append(
                            {
                                "id": chunk_obj.id,
                                "document_id": document.id,
                                "chunk_index": chunk_obj.chunk_index,
                                "content": chunk_obj.chunk_text,
                                "insurance_company": document.insurance_company.name,
                                "document_title": document.title,
                                "created_at": (
                                    chunk_obj.created_at.isoformat()
                                    if chunk_obj.created_at
                                    else ""
                                ),
                            }
                        )

                    # Embedding 처리 및 Pinecone 업로드
                    if chunk_data:
                        success = embedding_service.process_document_chunks(chunk_data)
                        if success:
                            messages.success(
                                request,
                                "문서가 성공적으로 재처리되었습니다. (Embedding 완료)",
                            )
                        else:
                            messages.warning(
                                request,
                                "문서는 재처리되었지만 Embedding 처리에 실패했습니다.",
                            )
                    else:
                        messages.success(request, "문서가 성공적으로 재처리되었습니다.")

                except Exception as e:
                    messages.warning(
                        request,
                        f"문서는 재처리되었지만 Embedding 처리 중 오류가 발생했습니다: {str(e)}",
                    )

                document.status = "completed"
                document.processed_at = datetime.now()
                document.save()
            else:
                messages.error(request, "텍스트 추출에 실패했습니다.")

        except Exception as e:
            messages.error(request, f"문서 재처리 중 오류가 발생했습니다: {str(e)}")

        return redirect("chatbot:document_detail", document_id=document.id)

    return render(
        request,
        "chatbot/document_process.jinja.html",
        {"title": "문서 재처리", "document": document},
    )


@admin_required
def embedding_stats_view(request):
    """Embedding 통계 뷰"""
    try:
        embedding_service = DocumentEmbeddingService()
        stats = embedding_service.get_index_statistics()

        # 문서 통계 추가
        total_documents = InsuranceDocument.objects.count()
        total_chunks = DocumentChunk.objects.count()
        completed_documents = InsuranceDocument.objects.filter(
            status="completed"
        ).count()

        context = {
            "title": "Embedding 통계",
            "pinecone_stats": stats,
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "completed_documents": completed_documents,
            "embedding_available": True,
        }

    except Exception as e:
        context = {
            "title": "Embedding 통계",
            "error_message": f"통계 조회 중 오류가 발생했습니다: {str(e)}",
            "embedding_available": False,
        }

    return render(request, "chatbot/embedding_stats.jinja.html", context)


@user_required
def search_documents_view(request):
    """문서 검색 뷰"""
    query = request.GET.get("q", "")
    insurance_company = request.GET.get("company", "")
    results = []

    if query:
        try:
            embedding_service = DocumentEmbeddingService()
            results = embedding_service.search_similar_chunks(
                query=query,
                top_k=10,
                insurance_company=insurance_company if insurance_company else None,
            )
        except Exception as e:
            messages.error(request, f"검색 중 오류가 발생했습니다: {str(e)}")

    # 보험사 목록
    companies = InsuranceCompany.objects.filter(is_active=True)

    context = {
        "title": "문서 검색",
        "query": query,
        "selected_company": insurance_company,
        "results": results,
        "companies": companies,
    }

    return render(request, "chatbot/search_documents.jinja.html", context)
