from django.core.management.base import BaseCommand
from django.db import transaction
from chatbot.models import InsuranceDocument, DocumentChunk
from chatbot.services import DocumentEmbeddingService, PineconeService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pinecone 인덱스를 완전히 재구축합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="확인 없이 인덱스를 재구축합니다.",
        )
        parser.add_argument(
            "--document-id",
            type=int,
            help="특정 문서만 재구축합니다.",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "정말로 Pinecone 인덱스를 완전히 재구축하시겠습니까? (y/N): "
                )
            )
            response = input().lower()
            if response != "y":
                self.stdout.write(self.style.ERROR("인덱스 재구축이 취소되었습니다."))
                return

        try:
            # Pinecone 서비스 초기화
            pinecone_service = PineconeService()
            embedding_service = DocumentEmbeddingService()

            # 기존 인덱스 삭제
            self.stdout.write(
                self.style.WARNING("기존 Pinecone 인덱스를 삭제합니다...")
            )
            try:
                pinecone_service.pc.delete_index(pinecone_service.index_name)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"인덱스 {pinecone_service.index_name} 삭제 완료"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"인덱스 삭제 중 오류 (무시): {e}")
                )

            # 새 인덱스 생성
            self.stdout.write(self.style.WARNING("새 Pinecone 인덱스를 생성합니다..."))
            pinecone_service._create_index()
            pinecone_service.index = pinecone_service.pc.Index(
                pinecone_service.index_name
            )

            # 문서 처리
            if options["document_id"]:
                documents = InsuranceDocument.objects.filter(id=options["document_id"])
                self.stdout.write(f'문서 ID {options["document_id"]}만 재구축합니다.')
            else:
                documents = InsuranceDocument.objects.all()
                self.stdout.write("모든 문서를 재구축합니다.")

            total_documents = documents.count()
            processed_documents = 0

            for document in documents:
                try:
                    self.stdout.write(
                        f"문서 처리 중: {document.title} (ID: {document.id})"
                    )

                    # 문서의 모든 청크 조회
                    chunks = DocumentChunk.objects.filter(document=document).order_by(
                        "chunk_index"
                    )

                    if not chunks.exists():
                        self.stdout.write(
                            self.style.WARNING(f"문서 {document.id}에 청크가 없습니다.")
                        )
                        continue

                    # 청크 데이터 준비
                    chunk_data = []
                    for chunk in chunks:
                        chunk_data.append(
                            {
                                "id": chunk.id,
                                "document_id": document.id,
                                "chunk_index": chunk.chunk_index,
                                "content": chunk.chunk_text,
                                "insurance_company": (
                                    document.insurance_company.name
                                    if document.insurance_company
                                    else "알 수 없는 보험사"
                                ),
                                "document_title": document.title,
                                "created_at": (
                                    chunk.created_at.isoformat()
                                    if chunk.created_at
                                    else ""
                                ),
                            }
                        )

                    # Embedding 처리 및 Pinecone 업로드
                    if chunk_data:
                        success = embedding_service.process_document_chunks(chunk_data)
                        if success:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"문서 {document.title} 처리 완료 ({len(chunk_data)}개 청크)"
                                )
                            )
                            processed_documents += 1
                        else:
                            self.stdout.write(
                                self.style.ERROR(f"문서 {document.title} 처리 실패")
                            )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"문서 {document.id} 처리 중 오류: {e}")
                    )

            self.stdout.write(self.style.SUCCESS(f"✅ Pinecone 인덱스 재구축 완료!"))
            self.stdout.write(
                self.style.SUCCESS(
                    f"처리된 문서: {processed_documents}/{total_documents}"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Pinecone 인덱스 재구축 실패: {e}"))
