from django.core.management.base import BaseCommand
from django.conf import settings
import openai


class Command(BaseCommand):
    help = "OpenAI 모델 테스트"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            help="테스트할 모델명 (기본값: 설정된 모델)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="사용 가능한 모델 목록 출력",
        )

    def handle(self, *args, **options):
        if not settings.OPENAI_API_KEY:
            self.stdout.write(self.style.ERROR("OpenAI API 키가 설정되지 않았습니다."))
            return

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        if options["list"]:
            self.list_models(client)
            return

        model = options["model"] or settings.OPENAI_MODEL
        self.test_model(client, model)

    def list_models(self, client):
        """사용 가능한 모델 목록 출력"""
        self.stdout.write(self.style.SUCCESS("사용 가능한 모델 목록:"))

        try:
            models = client.models.list()
            for model in models.data[:20]:  # 처음 20개만 출력
                self.stdout.write(f"- {model.id}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"모델 목록 조회 실패: {e}"))

    def test_model(self, client, model_name):
        """특정 모델 테스트"""
        self.stdout.write(self.style.SUCCESS(f"모델 테스트 시작: {model_name}"))

        # 테스트 메시지
        test_messages = [
            "안녕하세요",
            "자동차 보험에 대해 알려주세요",
            "보험금 청구 절차는 어떻게 되나요?",
        ]

        for i, message in enumerate(test_messages, 1):
            self.stdout.write(f'\n테스트 {i}: "{message}"')

            try:
                # 모델별 파라미터 설정
                api_params = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 자동차 보험 전문 상담사입니다.",
                        },
                        {"role": "user", "content": message},
                    ],
                }

                # gpt-5 모델들은 max_completion_tokens 사용
                if model_name.startswith("gpt-5"):
                    api_params["max_completion_tokens"] = 500
                    # gpt-5-nano는 특별한 설정 필요
                    if model_name == "gpt-5-nano":
                        api_params["max_completion_tokens"] = 1000
                        # gpt-5-nano는 temperature 파라미터 지원 안함
                else:
                    api_params["max_tokens"] = 500

                response = client.chat.completions.create(**api_params)

                if response.choices:
                    choice = response.choices[0]
                    if choice.message.content:
                        content = choice.message.content
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ 성공: {content[:50]}{"..." if len(content) > 50 else ""}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ 응답 없음 (finish_reason: {choice.finish_reason})"
                            )
                        )
                    
                    # 디버깅 정보 추가
                    self.stdout.write(f"   - finish_reason: {choice.finish_reason}")
                    self.stdout.write(f"   - usage: {response.usage}")
                    
                    # gpt-5-nano 디버깅을 위한 추가 정보
                    if model_name == "gpt-5-nano":
                        self.stdout.write(f"   - message content length: {len(choice.message.content) if choice.message.content else 0}")
                        self.stdout.write(f"   - message content preview: {choice.message.content[:100] if choice.message.content else 'None'}")
                else:
                    self.stdout.write(self.style.ERROR("❌ 응답에 choices가 없습니다"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ 실패: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n모델 테스트 완료: {model_name}"))
