from django.core.management.base import BaseCommand
from chatbot.services import PineconeService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Pinecone 인덱스를 삭제하고 재생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-only',
            action='store_true',
            help='인덱스만 삭제하고 재생성하지 않습니다.',
        )
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='인덱스를 삭제하고 재생성합니다.',
        )

    def handle(self, *args, **options):
        try:
            pinecone_service = PineconeService()
            
            if options['delete_only']:
                # 인덱스만 삭제
                if pinecone_service.delete_index():
                    self.stdout.write(
                        self.style.SUCCESS('✅ Pinecone 인덱스가 성공적으로 삭제되었습니다.')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('❌ Pinecone 인덱스 삭제에 실패했습니다.')
                    )
                    
            elif options['recreate']:
                # 인덱스 삭제 후 재생성
                if pinecone_service.recreate_index():
                    self.stdout.write(
                        self.style.SUCCESS('✅ Pinecone 인덱스가 성공적으로 재생성되었습니다.')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('❌ Pinecone 인덱스 재생성에 실패했습니다.')
                    )
            else:
                # 기본: 모든 벡터만 삭제
                if pinecone_service.delete_all_vectors():
                    self.stdout.write(
                        self.style.SUCCESS('✅ Pinecone 인덱스의 모든 벡터가 삭제되었습니다.')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('❌ Pinecone 벡터 삭제에 실패했습니다.')
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 오류가 발생했습니다: {str(e)}')
            )
            logger.error(f"Pinecone 인덱스 관리 중 오류: {e}")
