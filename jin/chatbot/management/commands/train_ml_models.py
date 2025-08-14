from django.core.management.base import BaseCommand
from chatbot.ml_models import InsurancePremiumPredictor
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "보험료 예측을 위한 ML 모델을 훈련합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--samples",
            type=int,
            default=2000,
            help="훈련 데이터 샘플 수 (기본값: 2000)",
        )
        parser.add_argument(
            "--force", action="store_true", help="기존 모델을 덮어씁니다"
        )

    def handle(self, *args, **options):
        samples = options["samples"]
        force = options["force"]

        self.stdout.write(
            self.style.SUCCESS(f"🤖 ML 모델 훈련을 시작합니다... (샘플 수: {samples})")
        )

        try:
            # ML 모델 초기화
            predictor = InsurancePremiumPredictor()

            # 기존 모델 확인
            if predictor.model is not None and not force:
                self.stdout.write(
                    self.style.WARNING(
                        "기존 모델이 이미 로드되어 있습니다. --force 옵션을 사용하여 재훈련하세요."
                    )
                )
                return

            # 모델 훈련
            self.stdout.write("📊 모의 훈련 데이터 생성 중...")
            metrics = predictor.train_model()

            # 결과 출력
            self.stdout.write(self.style.SUCCESS("✅ 모델 훈련이 완료되었습니다!"))

            self.stdout.write(f"📈 모델 성능:")
            self.stdout.write(f'   • MAE (평균 절대 오차): {metrics["mae"]:,.0f}원')
            self.stdout.write(f'   • RMSE (평균 제곱근 오차): {metrics["rmse"]:,.0f}원')
            self.stdout.write(f'   • R² (결정 계수): {metrics["r2"]:.3f}')
            self.stdout.write(
                f'   • MAPE (평균 절대 백분율 오차): {metrics["mape"]:.1f}%'
            )

            # 특성 중요도 출력
            feature_importance = predictor.get_feature_importance()
            if feature_importance:
                self.stdout.write(f"🎯 특성 중요도:")
                for feature, importance in sorted(
                    feature_importance.items(), key=lambda x: x[1], reverse=True
                ):
                    self.stdout.write(f"   • {feature}: {importance:.3f}")

            self.stdout.write(self.style.SUCCESS("💾 모델이 저장되었습니다."))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ 모델 훈련 중 오류가 발생했습니다: {e}")
            )
            logger.error(f"ML 모델 훈련 중 오류: {e}")
            raise
