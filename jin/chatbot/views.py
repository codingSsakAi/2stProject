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
from django.conf import settings
import os
import json
from .models import InsuranceDocument, DocumentChunk, InsuranceCompany
from .forms import DocumentUploadForm
from .utils import PDFProcessor
from .services import DocumentEmbeddingService
from datetime import datetime
from .models import ChatSession, ChatHistory
from django.utils import timezone
from django.core.paginator import Paginator
from .decorators import admin_required, user_required, chatbot_access_required
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

# Create your views here.


@chatbot_access_required
def chat_view(request):
    """RAG 챗봇 상담 뷰 (실시간 채팅)"""

    # URL 파라미터에서 세션 ID 확인
    session_id = request.GET.get("session_id")

    # 채팅 세션 목록 조회
    chat_sessions = ChatSession.objects.filter(user=request.user).order_by(
        "-updated_at"
    )

    # URL 파라미터에서 새 대화 요청 확인
    new_chat = request.GET.get("new_chat") == "true"

    # 특정 세션이 요청된 경우 해당 세션 사용
    if session_id:
        current_session = get_object_or_404(
            ChatSession, id=session_id, user=request.user
        )
    # 새 대화 요청인 경우 새로운 세션 생성
    elif new_chat:
        current_session = ChatSession.objects.create(
            user=request.user, title="새로운 채팅"
        )
        # 새 대화 생성 후 URL에서 파라미터 제거를 위해 리다이렉트
        from django.shortcuts import redirect

        return redirect("chatbot:chat")
    # 그 외의 경우 최근 세션 사용
    else:
        current_session = chat_sessions.first()
        # 세션이 없으면 새로 생성
        if not current_session:
            current_session = ChatSession.objects.create(
                user=request.user, title="새로운 채팅"
            )

    # 현재 세션의 채팅 기록 (시간 순서)
    chat_history = []
    if current_session:
        chat_history = ChatHistory.objects.filter(session=current_session).order_by(
            "created_at"
        )  # 시간 순서대로

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

    # 페이징을 위한 세션 목록 처리
    paginator = Paginator(chat_sessions, 10)  # 페이지당 10개
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "title": "챗봇 상담",
        "chat_sessions": page_obj,
        "current_session": current_session,
        "chat_history": chat_history,
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

        # 현재 활성 세션 확인
        session_id = data.get("session_id")
        if session_id:
            try:
                chat_session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                # 세션이 존재하지 않으면 새로 생성
                chat_session = ChatSession.objects.create(
                    user=request.user, title=user_message[:50] + "..."
                )
                logger.info(
                    f"새 세션 생성: {chat_session.id}, 제목: {chat_session.title}"
                )
        else:
            # 세션 ID가 없으면 첫 번째 세션 사용
            chat_session = ChatSession.objects.filter(user=request.user).first()
            if not chat_session:
                # 새 세션 생성 시 첫 메시지를 제목으로 설정
                chat_session = ChatSession.objects.create(
                    user=request.user, title=user_message[:50] + "..."
                )
                logger.info(
                    f"새 세션 생성: {chat_session.id}, 제목: {chat_session.title}"
                )
            # 기존 세션의 제목이 기본값인 경우 첫 메시지로 제목 업데이트
            elif chat_session.title == "새로운 채팅":
                chat_session.title = user_message[:50] + "..."
                chat_session.save()
                logger.info(
                    f"세션 제목 업데이트: {chat_session.id}, 새 제목: {chat_session.title}"
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

        # 제목 업데이트 여부 확인 (첫 번째 메시지일 때)
        title_updated = False
        new_title = None

        # 현재 세션의 메시지 수 확인 (사용자 메시지 + 봇 메시지)
        message_count = ChatHistory.objects.filter(session=chat_session).count()
        logger.info(
            f"현재 세션 메시지 수: {message_count}, 세션 제목: {chat_session.title}"
        )

        # 첫 번째 메시지이고 제목이 "새로운 채팅"인 경우에만 제목 업데이트
        if message_count == 2 and chat_session.title == "새로운 채팅":
            # 사용자 메시지를 제목으로 설정 (최대 50자)
            new_title = user_message[:50] + ("..." if len(user_message) > 50 else "")
            chat_session.title = new_title
            chat_session.save()
            title_updated = True
            logger.info(f"세션 제목 업데이트: {new_title}")

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
            "title_updated": title_updated,
            "new_title": new_title,
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

        # 디버깅 로그 - 받은 데이터 확인
        logger.info(f"받은 프로필 데이터: {data}")
        logger.info(f"사용자 ID: {request.user.id}")

        # 사용자 프로필 업데이트 또는 생성
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        logger.info(f"프로필 생성/조회: created={created}, profile_id={profile.id}")

        # 입력받은 데이터로 프로필 업데이트 (기존 방식으로 복원)
        # 각 필드 업데이트 및 로깅
        if "birth_date" in data and data["birth_date"]:
            try:
                from datetime import datetime

                profile.birth_date = datetime.strptime(
                    data["birth_date"], "%Y-%m-%d"
                ).date()
                logger.info(f"생년월일 업데이트: {profile.birth_date}")
            except (ValueError, TypeError):
                profile.birth_date = None
                logger.warning(f"생년월일 파싱 실패: {data['birth_date']}")

        if "gender" in data:
            profile.gender = data["gender"]
            logger.info(f"성별 업데이트: {profile.gender}")

        if "residence_area" in data:
            profile.residence_area = data["residence_area"]
            logger.info(f"거주지 업데이트: {profile.residence_area}")

        if "driving_experience" in data:
            try:
                profile.driving_experience = int(data["driving_experience"])
                logger.info(f"운전경력 업데이트: {profile.driving_experience}")
            except (ValueError, TypeError):
                profile.driving_experience = 0
                logger.warning(f"운전경력 파싱 실패: {data['driving_experience']}")

        if "car_type" in data:
            profile.car_type = data["car_type"]
            logger.info(f"차종 업데이트: {profile.car_type}")

        if "annual_mileage" in data:
            try:
                profile.annual_mileage = int(data["annual_mileage"])
                logger.info(f"연간주행거리 업데이트: {profile.annual_mileage}")
            except (ValueError, TypeError):
                profile.annual_mileage = None
                logger.warning(f"연간주행거리 파싱 실패: {data['annual_mileage']}")

        if "accident_history" in data:
            try:
                profile.accident_history = int(data["accident_history"])
                logger.info(f"사고경력 업데이트: {profile.accident_history}")
            except (ValueError, TypeError):
                profile.accident_history = 0
                logger.warning(f"사고경력 파싱 실패: {data['accident_history']}")

        if "coverage_level" in data:
            profile.coverage_level = data["coverage_level"]
            logger.info(f"보장수준 업데이트: {profile.coverage_level}")

        if "additional_coverage_interest" in data:
            profile.additional_coverage_interest = bool(
                data["additional_coverage_interest"]
            )
            logger.info(
                f"추가특약관심 업데이트: {profile.additional_coverage_interest}"
            )

        profile.save()

        # 디버깅 로그
        logger.info(
            f"프로필 저장 완료: user_id={request.user.id}, profile_id={profile.id}"
        )
        logger.info(f"저장된 데이터: {data}")

        # 보험 추천 계산
        from .insurance_service import InsuranceRecommendationService
        from .services import RAGChatbotService

        insurance_service = InsuranceRecommendationService()

        # 현재 활성화된 채팅 세션 찾기
        session_id = data.get("session_id")
        if session_id:
            try:
                chat_session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                # 세션이 없으면 첫 번째 세션 사용
                chat_session = ChatSession.objects.filter(user=request.user).first()
                if not chat_session:
                    # 세션이 없으면 새로 생성
                    chat_session = ChatSession.objects.create(
                        user=request.user, title="보험 추천 상담"
                    )
        else:
            # 세션 ID가 없으면 첫 번째 세션 사용
            chat_session = ChatSession.objects.filter(user=request.user).first()
            if not chat_session:
                # 세션이 없으면 새로 생성
                chat_session = ChatSession.objects.create(
                    user=request.user, title="보험 추천 상담"
                )

        result = insurance_service.calculate_insurance_recommendations(
            request.user, "chatbot", chat_session
        )

        # 보험 추천 결과를 사용자 친화적인 형태로 포맷팅
        if isinstance(result, dict):
            # RAGChatbotService의 포맷팅 메서드 사용
            chatbot_service = RAGChatbotService()
            recommendation_text = chatbot_service._format_insurance_recommendation(
                result
            )
        else:
            recommendation_text = (
                str(result) if result else "보험 추천 결과를 생성할 수 없습니다."
            )

        # 사용자 메시지 저장 (보험 추천 요청)
        user_message = "자동차보험 추천해주세요"
        user_chat_history = ChatHistory.objects.create(
            user=request.user,
            session=chat_session,
            message=user_message,
            is_user=True,
        )

        # 보험 추천 답변을 데이터베이스에 저장
        bot_chat_history = ChatHistory.objects.create(
            user=request.user,
            session=chat_session,
            message=recommendation_text,
            is_user=False,
            metadata={
                "insurance_recommendation": True,
                "generated_at": timezone.now().isoformat(),
                "model_used": "insurance_service",
            },
        )

        # 세션 업데이트
        chat_session.updated_at = timezone.now()
        chat_session.save()

        logger.info(
            f"보험 추천 대화 저장 완료: session_id={chat_session.id}, user_message_id={user_chat_history.id}, bot_message_id={bot_chat_history.id}"
        )

        return JsonResponse(
            {
                "success": True,
                "message": "프로필 정보가 저장되었습니다.",
                "recommendation": recommendation_text,
                "session_id": chat_session.id,
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
            # 관련된 보험 추천 내역도 함께 삭제
            from accounts.models import InsuranceRecommendation

            InsuranceRecommendation.objects.filter(chat_session=chat_session).delete()

            # 채팅 세션 삭제 (ChatHistory는 CASCADE로 자동 삭제됨)
            chat_session.delete()
            messages.success(request, "채팅 세션과 관련 데이터가 삭제되었습니다.")
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

                # 동일한 제목과 보험사의 기존 문서 확인
                existing_document = InsuranceDocument.objects.filter(
                    title=title, insurance_company=insurance_company
                ).first()

                if existing_document:
                    # 기존 문서가 있으면 삭제
                    try:
                        # Pinecone에서 기존 벡터 삭제
                        embedding_service = DocumentEmbeddingService()
                        success = embedding_service.delete_document_vectors(existing_document.id)
                        if success:
                            logger.info(f"기존 문서 {existing_document.id}의 Pinecone 벡터 삭제 완료")
                        else:
                            logger.warning(f"기존 문서 {existing_document.id}의 Pinecone 벡터 삭제 실패")
                    except Exception as e:
                        logger.error(f"기존 문서 {existing_document.id}의 Pinecone 벡터 삭제 중 오류: {e}")

                    # 기존 청크 삭제
                    existing_document.chunks.all().delete()

                    # 기존 문서 삭제
                    existing_document.delete()
                    messages.info(request, "기존 문서를 삭제하고 새로 업로드합니다.")

                # PDF 처리기 초기화
                pdf_processor = PDFProcessor()

                # 문서 모델에 저장
                document = form.save(commit=False)
                document.uploaded_by = request.user
                document.status = "uploaded"
                document.save()

                # 진행상황 추적 시작
                from .models import ProcessingProgress

                progress = ProcessingProgress.objects.create(document=document)
                progress.add_log_message("문서 업로드 시작")

                # PDF 파일 경로
                pdf_path = document.pdf_file.path

                # 텍스트 추출 및 처리
                progress.update_progress("pdf_processing")
                progress.add_log_message("PDF 파일 처리 시작")

                text = pdf_processor.process_pdf_with_ocr(pdf_path)
                if text:
                    progress.update_progress("text_extraction")
                    progress.add_log_message("텍스트 추출 완료, 정리 중...")

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
                    document.processed_at = timezone.now()
                    document.save()

                    # 텍스트 청크 생성
                    progress.update_progress("chunk_creation")
                    progress.add_log_message("청크 생성 시작...")

                    chunks = pdf_processor.split_text_into_chunks(cleaned_text)
                    progress.update_progress("chunk_creation", total=len(chunks))
                    progress.add_log_message(f"총 {len(chunks)}개 청크 생성됨")

                    chunk_objects = []

                    # 메타데이터 서비스 초기화
                    from .metadata_service import MetadataService

                    metadata_service = MetadataService()

                    progress.update_progress("metadata_generation")
                    progress.add_log_message("메타데이터 생성 시작...")

                    for i, chunk_text in enumerate(chunks):
                        # 청크 생성
                        chunk_obj = DocumentChunk.objects.create(
                            document=document, chunk_text=chunk_text, chunk_index=i
                        )

                        # 메타데이터 생성
                        try:
                            metadata = metadata_service.generate_metadata(chunk_text)
                            chunk_obj.title = metadata.get("title", "")
                            chunk_obj.category = metadata.get("category", "기타")
                            chunk_obj.keywords = metadata.get("keywords", [])
                            chunk_obj.summary = metadata.get("summary", "")
                            chunk_obj.confidence_score = metadata.get(
                                "confidence_score", 0.0
                            )
                            chunk_obj.review_status = metadata.get(
                                "review_status", "pending"
                            )
                            chunk_obj.extraction_method = "llm_generated"
                            chunk_obj.save()

                            # 진행상황 업데이트
                            progress.update_progress(
                                "metadata_generation", processed=i + 1
                            )
                            if (i + 1) % 10 == 0:  # 10개마다 로그
                                progress.add_log_message(
                                    f"메타데이터 생성: {i+1}/{len(chunks)} 완료"
                                )

                        except Exception as e:
                            logger.warning(f"청크 {i} 메타데이터 생성 실패: {e}")
                            progress.add_log_message(
                                f"청크 {i} 메타데이터 생성 실패: {e}"
                            )

                        chunk_objects.append(chunk_obj)

                    # Embedding 처리 및 Pinecone 업로드
                    progress.update_progress("embedding_processing")
                    progress.add_log_message("Embedding 처리 시작...")

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
                        progress.update_progress("pinecone_upload")
                        progress.add_log_message("Pinecone 업로드 시작...")

                        if chunk_data:
                            success = embedding_service.process_document_chunks(
                                chunk_data
                            )
                            if success:
                                progress.complete(success=True)
                                progress.add_log_message("문서 처리 완료!")
                                messages.success(
                                    request,
                                    f"문서가 성공적으로 처리되었습니다. (Embedding 완료)",
                                )
                            else:
                                progress.complete(
                                    success=False, error_message="Embedding 처리 실패"
                                )
                                progress.add_log_message("Embedding 처리 실패")
                                messages.warning(
                                    request,
                                    f"문서는 처리되었지만 Embedding 처리에 실패했습니다.",
                                )
                        else:
                            progress.complete(success=True)
                            progress.add_log_message("문서 처리 완료!")
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
                success = embedding_service.delete_document_vectors(document.id)
                if success:
                    logger.info(f"문서 {document.id}의 Pinecone 벡터 삭제 완료")
                else:
                    logger.warning(f"문서 {document.id}의 Pinecone 벡터 삭제 실패")
            except Exception as e:
                logger.error(f"문서 {document.id}의 Pinecone 벡터 삭제 중 오류: {e}")
                # 벡터 삭제 실패해도 문서 삭제는 계속 진행

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

            # Pinecone에서 기존 벡터 삭제
            try:
                embedding_service = DocumentEmbeddingService()
                success = embedding_service.delete_document_vectors(document.id)
                if success:
                    logger.info(f"문서 {document.id}의 Pinecone 벡터 삭제 완료")
                else:
                    logger.warning(f"문서 {document.id}의 Pinecone 벡터 삭제 실패")
            except Exception as e:
                logger.error(f"문서 {document.id}의 Pinecone 벡터 삭제 중 오류: {e}")

            # PDF 처리기로 재처리
            pdf_processor = PDFProcessor()

            # txt 파일 경로 확인 및 생성
            txt_file_path = None
            if document.txt_file:
                txt_file_path = os.path.join(
                    settings.MEDIA_ROOT, document.txt_file.name
                )

            if txt_file_path and os.path.exists(txt_file_path):
                with open(txt_file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                text = pdf_processor.process_pdf_with_ocr(document.pdf_file.path)
                if text:
                    cleaned_text = pdf_processor.clean_text(text)

                    # txt 파일 경로 생성
                    if not txt_file_path:
                        txt_filename = f"{os.path.splitext(os.path.basename(document.pdf_file.name))[0]}.txt"
                        txt_file_path = os.path.join(
                            "media",
                            "documents",
                            "txt",
                            document.insurance_company.name,
                            txt_filename,
                        )
                        os.makedirs(os.path.dirname(txt_file_path), exist_ok=True)
                        document.txt_file = f"documents/txt/{document.insurance_company.name}/{txt_filename}"

                    # 텍스트 파일 업데이트
                    with open(txt_file_path, "w", encoding="utf-8") as f:
                        f.write(cleaned_text)
                    text = cleaned_text

            if text:
                # 텍스트 청크 재생성
                chunks = pdf_processor.split_text_into_chunks(text)
                chunk_objects = []

                # 메타데이터 서비스 초기화
                from .metadata_service import MetadataService

                metadata_service = MetadataService()

                for i, chunk_text in enumerate(chunks):
                    # 청크 생성
                    chunk_obj = DocumentChunk.objects.create(
                        document=document, chunk_text=chunk_text, chunk_index=i
                    )

                    # 메타데이터 생성
                    try:
                        metadata = metadata_service.generate_metadata(chunk_text)
                        chunk_obj.title = metadata.get("title", "")
                        chunk_obj.category = metadata.get("category", "기타")
                        chunk_obj.keywords = metadata.get("keywords", [])
                        chunk_obj.summary = metadata.get("summary", "")
                        chunk_obj.confidence_score = metadata.get(
                            "confidence_score", 0.0
                        )
                        chunk_obj.review_status = metadata.get(
                            "review_status", "pending"
                        )
                        chunk_obj.extraction_method = "llm_generated"
                        chunk_obj.save()
                    except Exception as e:
                        logger.warning(f"청크 {i} 메타데이터 생성 실패: {e}")

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
                document.processed_at = timezone.now()
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

        # 사용량 정보 추출
        usage_info = stats.get("usage_info", {})

        context = {
            "title": "Embedding 통계",
            "pinecone_stats": stats,
            "usage_info": usage_info,
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


@chatbot_access_required
@require_http_methods(["POST"])
def api_session_title(request):
    """세션 제목 수정 API"""
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")
        title = data.get("title", "").strip()

        if not session_id:
            return JsonResponse(
                {"success": False, "error": "세션 ID가 필요합니다."}, status=400
            )

        if not title:
            return JsonResponse(
                {"success": False, "error": "제목을 입력해주세요."}, status=400
            )

        # 세션 조회 및 수정
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.title = title
        session.save()

        return JsonResponse({"success": True, "message": "제목이 수정되었습니다."})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@chatbot_access_required
@require_http_methods(["POST"])
def api_session_delete(request):
    """세션 삭제 API"""
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")

        if not session_id:
            return JsonResponse(
                {"success": False, "error": "세션 ID가 필요합니다."}, status=400
            )

        # 세션 조회 및 삭제
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.delete()

        return JsonResponse({"success": True, "message": "세션이 삭제되었습니다."})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def api_get_chat_sessions(request):
    """AJAX로 페이징된 채팅 세션 목록을 반환하는 API"""
    try:
        page_number = int(request.GET.get("page", 1))
        search_query = request.GET.get("search", "").strip()

        # 기본 쿼리셋
        chat_sessions = ChatSession.objects.filter(user=request.user)

        # 검색 필터 적용
        if search_query:
            chat_sessions = chat_sessions.filter(title__icontains=search_query)

        # 최신순 정렬
        chat_sessions = chat_sessions.order_by("-updated_at")

        # 페이징
        paginator = Paginator(chat_sessions, 10)  # 페이지당 10개
        page_obj = paginator.get_page(page_number)

        # 세션 데이터 직렬화
        sessions_data = []
        current_session_id = request.GET.get("current_session_id", "0")

        for session in page_obj:
            try:
                is_current = (
                    session.id == int(current_session_id)
                    if current_session_id != "0"
                    else False
                )
            except (ValueError, TypeError):
                is_current = False

            # 메시지 개수 계산
            message_count = session.chat_history.count()

            sessions_data.append(
                {
                    "id": session.id,
                    "title": session.title or "새로운 채팅",
                    "created_at": session.created_at.strftime("%m/%d %H:%M"),
                    "message_count": message_count,
                    "is_current": is_current,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "sessions": sessions_data,
                "has_previous": page_obj.has_previous(),
                "has_next": page_obj.has_next(),
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
            }
        )

    except Exception as e:
        logger.error(f"채팅 세션 목록 조회 중 오류: {str(e)}")
        return JsonResponse(
            {
                "success": False,
                "error": "채팅 세션 목록을 불러오는 중 오류가 발생했습니다.",
            }
        )


@admin_required
@require_http_methods(["GET"])
def processing_progress_view(request, document_id):
    """문서 처리 진행상황 조회 API"""
    try:
        document = get_object_or_404(InsuranceDocument, id=document_id)
        progress = document.processing_progress.first()

        if not progress:
            return JsonResponse(
                {"success": False, "error": "진행상황 정보를 찾을 수 없습니다."}
            )

        return JsonResponse(
            {
                "success": True,
                "progress": {
                    "current_stage": progress.current_stage,
                    "total_chunks": progress.total_chunks,
                    "processed_chunks": progress.processed_chunks,
                    "progress_percentage": progress.progress_percentage,
                    "log_messages": progress.log_messages[-10:],  # 최근 10개만
                    "started_at": progress.started_at.isoformat(),
                    "updated_at": progress.updated_at.isoformat(),
                    "completed_at": (
                        progress.completed_at.isoformat()
                        if progress.completed_at
                        else None
                    ),
                    "error_message": progress.error_message,
                    "is_completed": progress.current_stage in ["completed", "error"],
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": f"진행상황 조회 중 오류가 발생했습니다: {str(e)}",
            }
        )
