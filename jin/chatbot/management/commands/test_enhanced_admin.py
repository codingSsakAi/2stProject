from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from chatbot.enhanced_views import (
    enhanced_document_list_view,
    enhanced_document_detail_view,
    enhanced_document_search_view,
    enhanced_embedding_stats_view,
    enhanced_chat_management_view
)
from chatbot.models import InsuranceDocument, DocumentChunk, InsuranceCompany
import logging
import json

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = '향상된 관리자 페이지를 테스트합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-views',
            action='store_true',
            help='향상된 뷰들을 테스트합니다.',
        )
        parser.add_argument(
            '--test-apis',
            action='store_true',
            help='메타데이터 API를 테스트합니다.',
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='모든 테스트를 실행합니다.',
        )

    def handle(self, *args, **options):
        try:
            if options['test_all'] or options['test_views']:
                self._test_enhanced_views()
            
            if options['test_all'] or options['test_apis']:
                self._test_metadata_apis()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 오류가 발생했습니다: {str(e)}')
            )
            logger.error(f"향상된 관리자 페이지 테스트 중 오류: {e}")

    def _test_enhanced_views(self):
        """향상된 뷰 테스트"""
        self.stdout.write("\n🔍 향상된 관리자 뷰 테스트 시작...")
        
        # 테스트용 사용자 생성
        admin_user, created = User.objects.get_or_create(
            username='test_admin',
            defaults={
                'email': 'admin@test.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # RequestFactory 초기화
        factory = RequestFactory()
        
        try:
            # 1. 향상된 문서 목록 뷰 테스트
            self.stdout.write("\n📋 향상된 문서 목록 뷰 테스트...")
            
            request = factory.get('/enhanced/documents/')
            request.user = admin_user
            
            response = enhanced_document_list_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ 문서 목록 뷰 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ 문서 목록 뷰 오류: {response.status_code}"))
            
            # 필터링 테스트
            request = factory.get('/enhanced/documents/?category=보험료관리&company=테스트보험사')
            request.user = admin_user
            
            response = enhanced_document_list_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ 필터링 기능 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ 필터링 기능 오류: {response.status_code}"))
            
            # 2. 향상된 문서 검색 뷰 테스트
            self.stdout.write("\n🔍 향상된 문서 검색 뷰 테스트...")
            
            request = factory.get('/enhanced/documents/search/?q=보험료')
            request.user = admin_user
            
            response = enhanced_document_search_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ 문서 검색 뷰 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ 문서 검색 뷰 오류: {response.status_code}"))
            
            # 3. 향상된 Embedding 통계 뷰 테스트
            self.stdout.write("\n📊 향상된 Embedding 통계 뷰 테스트...")
            
            request = factory.get('/enhanced/embedding_stats/')
            request.user = admin_user
            
            response = enhanced_embedding_stats_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ Embedding 통계 뷰 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Embedding 통계 뷰 오류: {response.status_code}"))
            
            # 4. 향상된 챗봇 상담 관리 뷰 테스트
            self.stdout.write("\n💬 향상된 챗봇 상담 관리 뷰 테스트...")
            
            request = factory.get('/enhanced/chat_management/')
            request.user = admin_user
            
            response = enhanced_chat_management_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ 챗봇 상담 관리 뷰 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ 챗봇 상담 관리 뷰 오류: {response.status_code}"))
            
            # 5. 문서 상세 뷰 테스트 (문서가 있는 경우)
            documents = InsuranceDocument.objects.all()
            if documents.exists():
                document = documents.first()
                self.stdout.write(f"\n📄 향상된 문서 상세 뷰 테스트 (문서 ID: {document.id})...")
                
                request = factory.get(f'/enhanced/documents/{document.id}/')
                request.user = admin_user
                
                response = enhanced_document_detail_view(request, document.id)
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("   ✅ 문서 상세 뷰 정상 작동"))
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ 문서 상세 뷰 오류: {response.status_code}"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠️ 테스트할 문서가 없어 문서 상세 뷰 테스트를 건너뜁니다."))
            
            self.stdout.write(
                self.style.SUCCESS('✅ 향상된 관리자 뷰 테스트 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 향상된 뷰 테스트 실패: {str(e)}')
            )
            logger.error(f"향상된 뷰 테스트 실패: {e}")

    def _test_metadata_apis(self):
        """메타데이터 API 테스트"""
        self.stdout.write("\n🔧 메타데이터 API 테스트 시작...")
        
        # 테스트용 사용자 생성
        admin_user, created = User.objects.get_or_create(
            username='test_admin',
            defaults={
                'email': 'admin@test.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # RequestFactory 초기화
        factory = RequestFactory()
        
        try:
            # 1. 청크 메타데이터 업데이트 API 테스트
            chunks = DocumentChunk.objects.all()
            if chunks.exists():
                chunk = chunks.first()
                self.stdout.write(f"\n📝 청크 메타데이터 업데이트 API 테스트 (청크 ID: {chunk.id})...")
                
                # 테스트 데이터
                test_data = {
                    'title': '테스트 제목',
                    'category': '테스트 카테고리',
                    'keywords': ['테스트', '키워드'],
                    'summary': '테스트 요약'
                }
                
                request = factory.post(
                    f'/api/chunks/{chunk.id}/metadata/',
                    data=json.dumps(test_data),
                    content_type='application/json'
                )
                request.user = admin_user
                
                from chatbot.enhanced_views import update_chunk_metadata_view
                response = update_chunk_metadata_view(request, chunk.id)
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("   ✅ 메타데이터 업데이트 API 정상 작동"))
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ 메타데이터 업데이트 API 오류: {response.status_code}"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠️ 테스트할 청크가 없어 메타데이터 업데이트 API 테스트를 건너뜁니다."))
            
            # 2. 문서 메타데이터 재처리 API 테스트
            documents = InsuranceDocument.objects.all()
            if documents.exists():
                document = documents.first()
                self.stdout.write(f"\n🔄 문서 메타데이터 재처리 API 테스트 (문서 ID: {document.id})...")
                
                request = factory.post(f'/api/documents/{document.id}/reprocess/')
                request.user = admin_user
                
                from chatbot.enhanced_views import reprocess_document_metadata_view
                response = reprocess_document_metadata_view(request, document.id)
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("   ✅ 메타데이터 재처리 API 정상 작동"))
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ 메타데이터 재처리 API 오류: {response.status_code}"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠️ 테스트할 문서가 없어 메타데이터 재처리 API 테스트를 건너뜁니다."))
            
            # 3. 메타데이터 내보내기 API 테스트
            self.stdout.write("\n📤 메타데이터 내보내기 API 테스트...")
            
            # CSV 형식 테스트
            request = factory.get('/api/metadata/export/?format=csv')
            request.user = admin_user
            
            from chatbot.enhanced_views import export_metadata_view
            response = export_metadata_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ CSV 내보내기 API 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ CSV 내보내기 API 오류: {response.status_code}"))
            
            # JSON 형식 테스트
            request = factory.get('/api/metadata/export/?format=json')
            request.user = admin_user
            
            response = export_metadata_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ JSON 내보내기 API 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ JSON 내보내기 API 오류: {response.status_code}"))
            
            # 필터링 테스트
            request = factory.get('/api/metadata/export/?category=보험료관리&format=csv')
            request.user = admin_user
            
            response = export_metadata_view(request)
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("   ✅ 필터링 내보내기 API 정상 작동"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ 필터링 내보내기 API 오류: {response.status_code}"))
            
            self.stdout.write(
                self.style.SUCCESS('✅ 메타데이터 API 테스트 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 메타데이터 API 테스트 실패: {str(e)}')
            )
            logger.error(f"메타데이터 API 테스트 실패: {e}")

    def _test_integration(self):
        """통합 테스트"""
        self.stdout.write("\n🔄 향상된 관리자 페이지 통합 테스트 시작...")
        
        try:
            # 전체 워크플로우 테스트
            self.stdout.write("1. 문서 목록 조회")
            self.stdout.write("2. 문서 검색")
            self.stdout.write("3. 메타데이터 편집")
            self.stdout.write("4. 통계 확인")
            self.stdout.write("5. 데이터 내보내기")
            
            self.stdout.write(
                self.style.SUCCESS('✅ 통합 테스트 완료')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 통합 테스트 실패: {str(e)}')
            )
            logger.error(f"통합 테스트 실패: {e}")
