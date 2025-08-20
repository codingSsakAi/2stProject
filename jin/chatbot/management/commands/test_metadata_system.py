from django.core.management.base import BaseCommand
from chatbot.metadata_service import MetadataService
from chatbot.keyword_mapper import KeywordMapper
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "메타데이터 시스템을 테스트합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-chunks",
            action="store_true",
            help="청크 메타데이터 생성 테스트를 실행합니다.",
        )
        parser.add_argument(
            "--test-keywords",
            action="store_true",
            help="키워드 매핑 테스트를 실행합니다.",
        )
        parser.add_argument(
            "--test-all",
            action="store_true",
            help="모든 테스트를 실행합니다.",
        )

    def handle(self, *args, **options):
        try:
            if options["test_all"] or options["test_chunks"]:
                self._test_chunk_metadata()

            if options["test_all"] or options["test_keywords"]:
                self._test_keyword_mapping()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 오류가 발생했습니다: {str(e)}"))
            logger.error(f"메타데이터 시스템 테스트 중 오류: {e}")

    def _test_chunk_metadata(self):
        """청크 메타데이터 생성 테스트"""
        self.stdout.write("\n🧪 청크 메타데이터 생성 테스트 시작...")

        metadata_service = MetadataService()

        # 테스트용 청크들
        test_chunks = [
            "제1조(목적) 이 약관은 자동차보험 계약에 관한 사항을 규정합니다.",
            "제2조(보험료) 계약자는 보험료를 납입할 의무가 있습니다. 보험료 납입이 연체되면 계약이 해지될 수 있습니다.",
            "제3조(보험금지급) 보험사고 발생 시 보험금을 지급합니다. 단, 면책사유에 해당하는 경우 지급하지 않습니다.",
            "제4조(면책사유) 고의사고, 무면허운전, 음주운전의 경우 보험금을 지급하지 않습니다.",
            "제5조(사고신고) 사고 발생 시 24시간 이내에 보험사에 신고해야 합니다.",
        ]

        document_info = {
            "total_pages": 10,
            "insurance_company": "테스트보험사",
            "document_title": "테스트 약관",
        }

        try:
            # 메타데이터 생성
            metadata_list = metadata_service.process_document_chunks(
                test_chunks, document_info
            )

            # 결과 출력
            for i, metadata in enumerate(metadata_list):
                self.stdout.write(f"\n📄 청크 {i+1}:")
                self.stdout.write(f"   제목: {metadata.get('title', 'N/A')}")
                self.stdout.write(f"   카테고리: {metadata.get('category', 'N/A')}")
                self.stdout.write(
                    f"   조문번호: {metadata.get('article_number', 'N/A')}"
                )
                self.stdout.write(
                    f"   키워드: {', '.join(metadata.get('keywords', []))}"
                )
                self.stdout.write(f"   요약: {metadata.get('summary', 'N/A')}")
                self.stdout.write(
                    f"   신뢰도: {metadata.get('confidence_score', 0.0):.2f}"
                )
                self.stdout.write(
                    f"   검토상태: {metadata.get('review_status', 'N/A')}"
                )

            # 통계 정보
            stats = metadata_service.get_metadata_statistics(metadata_list)
            self.stdout.write(f"\n📊 메타데이터 통계:")
            self.stdout.write(f"   총 청크 수: {stats['total_chunks']}")
            self.stdout.write(f"   평균 신뢰도: {stats['avg_confidence']:.2f}")
            self.stdout.write(f"   카테고리 분포: {stats['categories']}")
            self.stdout.write(f"   검토 상태: {stats['review_status']}")

            self.stdout.write(self.style.SUCCESS("✅ 청크 메타데이터 생성 테스트 완료"))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ 청크 메타데이터 테스트 실패: {str(e)}")
            )
            logger.error(f"청크 메타데이터 테스트 중 오류: {e}")

    def _test_keyword_mapping(self):
        """키워드 매핑 테스트"""
        self.stdout.write("\n🔍 키워드 매핑 테스트 시작...")

        keyword_mapper = KeywordMapper()

        # 테스트용 질문들
        test_questions = [
            "연봉 5000만원인 회사원의 세금은 얼마나 내야하나?",
            "자동차보험 가입자는 언제까지 보험료를 내야해?",
            "사고가 났는데 어디서 보험금을 받을 수 있어?",
            "무면허운전하면 보험금을 안줘나?",
            "보험료를 연체하면 어떻게 되나?",
        ]

        try:
            for i, question in enumerate(test_questions):
                self.stdout.write(f"\n❓ 질문 {i+1}: {question}")

                # 키워드 매핑
                mapped_question = keyword_mapper.map_keywords(question)
                self.stdout.write(f"   매핑 결과: {mapped_question}")

                # 키워드 추출
                extracted_keywords = keyword_mapper.extract_keywords_from_text(question)
                self.stdout.write(f"   추출된 키워드: {', '.join(extracted_keywords)}")

            # 키워드 통계
            stats = keyword_mapper.get_keyword_statistics()
            self.stdout.write(f"\n📊 키워드 매핑 통계:")
            self.stdout.write(f"   총 매핑 수: {stats['total_mappings']}")
            self.stdout.write(
                f"   고유 전문 키워드: {stats['unique_professional_keywords']}"
            )
            self.stdout.write(f"   카테고리별 분포: {stats['categories']}")

            self.stdout.write(self.style.SUCCESS("✅ 키워드 매핑 테스트 완료"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 키워드 매핑 테스트 실패: {str(e)}"))
            logger.error(f"키워드 매핑 테스트 중 오류: {e}")

    def _test_integration(self):
        """통합 테스트"""
        self.stdout.write("\n🔄 메타데이터 시스템 통합 테스트 시작...")

        try:
            # 전체 파이프라인 테스트
            test_content = "자동차보험 계약자는 보험료를 납입할 의무가 있습니다. 보험료 납입이 연체되면 계약이 해지될 수 있습니다."

            metadata_service = MetadataService()
            keyword_mapper = KeywordMapper()

            # 1. 키워드 매핑
            mapped_content = keyword_mapper.map_keywords(test_content)
            self.stdout.write(f"키워드 매핑: {mapped_content}")

            # 2. 메타데이터 생성
            metadata_list = metadata_service.process_document_chunks([test_content])
            metadata = metadata_list[0]

            self.stdout.write(f"메타데이터 생성:")
            self.stdout.write(f"  - 제목: {metadata.get('title')}")
            self.stdout.write(f"  - 카테고리: {metadata.get('category')}")
            self.stdout.write(f"  - 키워드: {metadata.get('keywords')}")
            self.stdout.write(f"  - 신뢰도: {metadata.get('confidence_score')}")

            self.stdout.write(self.style.SUCCESS("✅ 통합 테스트 완료"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 통합 테스트 실패: {str(e)}"))
            logger.error(f"통합 테스트 중 오류: {e}")
