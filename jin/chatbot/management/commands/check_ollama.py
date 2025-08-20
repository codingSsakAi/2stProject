from django.core.management.base import BaseCommand
from chatbot.llm_service import OllamaLLMService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ollama 로컬 LLM 상태를 확인합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test",
            action="store_true",
            help="간단한 테스트를 실행합니다.",
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write("🔍 Ollama 상태 확인 중...")

            # Ollama 서비스 초기화
            ollama_service = OllamaLLMService()

            # 사용 가능 여부 확인
            if ollama_service.is_available():
                self.stdout.write(
                    self.style.SUCCESS("✅ Ollama가 정상적으로 초기화되었습니다.")
                )
                self.stdout.write(f"   모델: {ollama_service.model_name}")
                self.stdout.write(f"   엔드포인트: http://localhost:11434")

                # 테스트 실행
                if options["test"]:
                    self._run_test(ollama_service)
            else:
                self.stdout.write(self.style.ERROR("❌ Ollama를 사용할 수 없습니다."))
                self.stdout.write("   다음 사항을 확인하세요:")
                self.stdout.write("   1. Ollama가 설치되어 있는지 확인")
                self.stdout.write("   2. Ollama 서비스가 실행 중인지 확인")
                self.stdout.write(
                    "   3. exaone3.5:2.4b 모델이 다운로드되어 있는지 확인"
                )
                self.stdout.write(
                    "   4. langchain-community 패키지가 설치되어 있는지 확인"
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 오류가 발생했습니다: {str(e)}"))
            logger.error(f"Ollama 상태 확인 중 오류: {e}")

    def _run_test(self, ollama_service):
        """간단한 테스트 실행"""
        self.stdout.write("\n🧪 간단한 테스트 실행 중...")

        test_content = "자동차보험 계약자는 보험료를 납입할 의무가 있습니다. 보험료 납입이 연체되면 계약이 해지될 수 있습니다."

        try:
            # 제목 추출 테스트
            title = ollama_service.extract_title(test_content)
            self.stdout.write(f"   제목 추출: {title}")

            # 카테고리 분류 테스트
            category = ollama_service.classify_category(test_content)
            self.stdout.write(f"   카테고리 분류: {category}")

            # 키워드 추출 테스트
            keywords = ollama_service.extract_keywords(test_content, 3)
            self.stdout.write(f"   키워드 추출: {', '.join(keywords)}")

            # 요약 생성 테스트
            summary = ollama_service.generate_summary(test_content, 50)
            self.stdout.write(f"   요약 생성: {summary}")

            self.stdout.write(
                self.style.SUCCESS("✅ 모든 테스트가 성공적으로 완료되었습니다.")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ 테스트 중 오류가 발생했습니다: {str(e)}")
            )
            logger.error(f"Ollama 테스트 중 오류: {e}")
