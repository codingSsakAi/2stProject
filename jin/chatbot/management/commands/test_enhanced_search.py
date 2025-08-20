from django.core.management.base import BaseCommand
from chatbot.enhanced_search import EnhancedSearchService
from chatbot.search_metrics import SearchPerformanceMonitor
from chatbot.services import DocumentService, EmbeddingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "향상된 검색 시스템을 테스트합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-basic",
            action="store_true",
            help="기본 검색 기능을 테스트합니다.",
        )
        parser.add_argument(
            "--test-filters",
            action="store_true",
            help="메타데이터 필터링을 테스트합니다.",
        )
        parser.add_argument(
            "--test-metrics",
            action="store_true",
            help="검색 메트릭을 테스트합니다.",
        )
        parser.add_argument(
            "--test-all",
            action="store_true",
            help="모든 테스트를 실행합니다.",
        )

    def handle(self, *args, **options):
        try:
            # 서비스 초기화
            embedding_service = EmbeddingService()
            document_service = DocumentService(embedding_service)
            enhanced_search = EnhancedSearchService(document_service, embedding_service)
            performance_monitor = SearchPerformanceMonitor()

            if options["test_all"] or options["test_basic"]:
                self._test_basic_search(enhanced_search, performance_monitor)

            if options["test_all"] or options["test_filters"]:
                self._test_metadata_filters(enhanced_search, performance_monitor)

            if options["test_all"] or options["test_metrics"]:
                self._test_search_metrics(performance_monitor)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 오류가 발생했습니다: {str(e)}"))
            logger.error(f"향상된 검색 테스트 중 오류: {e}")

    def _test_basic_search(self, enhanced_search, performance_monitor):
        """기본 검색 기능 테스트"""
        self.stdout.write("\n🔍 기본 검색 기능 테스트 시작...")

        test_queries = [
            "자동차보험 보험료는 얼마나 내야하나?",
            "사고가 났을 때 보험금을 받을 수 있나?",
            "무면허운전하면 보험금을 안줘나?",
            "보험료를 연체하면 어떻게 되나?",
            "계약을 해지하고 싶으면 어떻게 해야 하나?",
        ]

        for i, query in enumerate(test_queries, 1):
            self.stdout.write(f"\n❓ 테스트 쿼리 {i}: {query}")

            try:
                # 성능 모니터링 시작
                performance_monitor.start_search(query, "enhanced")

                # 향상된 검색 수행
                search_results = enhanced_search.enhanced_search(query)

                # 성능 모니터링 종료
                performance_monitor.end_search(search_results)

                # 결과 출력
                self.stdout.write(f"   검색 결과: {len(search_results)}개")

                if search_results:
                    # 상위 3개 결과 표시
                    for j, result in enumerate(search_results[:3], 1):
                        final_score = result.get("final_score", 0)
                        search_type = result.get("search_type", "unknown")
                        metadata = result.get("metadata", {})

                        self.stdout.write(
                            f"   결과 {j}: 점수={final_score:.3f}, 유형={search_type}"
                        )
                        if metadata.get("title"):
                            self.stdout.write(f"      제목: {metadata['title']}")
                        if metadata.get("category"):
                            self.stdout.write(f"      카테고리: {metadata['category']}")

                # 검색 통계
                stats = enhanced_search.get_search_statistics(search_results)
                self.stdout.write(f"   평균 점수: {stats.get('avg_score', 0):.3f}")
                self.stdout.write(f"   검색 유형: {stats.get('search_types', {})}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ 검색 실패: {str(e)}"))
                logger.error(f"기본 검색 테스트 실패: {e}")

        self.stdout.write(self.style.SUCCESS("✅ 기본 검색 기능 테스트 완료"))

    def _test_metadata_filters(self, enhanced_search, performance_monitor):
        """메타데이터 필터링 테스트"""
        self.stdout.write("\n🔍 메타데이터 필터링 테스트 시작...")

        test_cases = [
            {
                "query": "보험료 관련 정보",
                "category_filter": "보험료관리",
                "description": "카테고리 필터링",
            },
            {
                "query": "보험금 지급 조건",
                "category_filter": "보험금지급",
                "description": "보험금 카테고리 필터링",
            },
            {
                "query": "면책 사유",
                "category_filter": "면책/배상",
                "description": "면책 카테고리 필터링",
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            self.stdout.write(f"\n📋 테스트 케이스 {i}: {test_case['description']}")
            self.stdout.write(f"   쿼리: {test_case['query']}")
            self.stdout.write(f"   필터: 카테고리={test_case['category_filter']}")

            try:
                # 성능 모니터링 시작
                performance_monitor.start_search(test_case["query"], "filtered")

                # 필터링된 검색 수행
                search_results = enhanced_search.enhanced_search(
                    query=test_case["query"],
                    category_filter=test_case["category_filter"],
                )

                # 성능 모니터링 종료
                performance_monitor.end_search(search_results)

                # 결과 분석
                self.stdout.write(f"   필터링된 결과: {len(search_results)}개")

                if search_results:
                    # 카테고리 분포 확인
                    categories = {}
                    for result in search_results:
                        category = result.get("metadata", {}).get("category", "기타")
                        categories[category] = categories.get(category, 0) + 1

                    self.stdout.write(f"   카테고리 분포: {categories}")

                    # 상위 결과 표시
                    top_result = search_results[0]
                    final_score = top_result.get("final_score", 0)
                    metadata = top_result.get("metadata", {})

                    self.stdout.write(f"   최고 점수: {final_score:.3f}")
                    if metadata.get("title"):
                        self.stdout.write(f"   최고 점수 제목: {metadata['title']}")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ 필터링 테스트 실패: {str(e)}")
                )
                logger.error(f"메타데이터 필터링 테스트 실패: {e}")

        self.stdout.write(self.style.SUCCESS("✅ 메타데이터 필터링 테스트 완료"))

    def _test_search_metrics(self, performance_monitor):
        """검색 메트릭 테스트"""
        self.stdout.write("\n📊 검색 메트릭 테스트 시작...")

        try:
            # 모니터링 데이터 가져오기
            monitoring_data = performance_monitor.get_monitoring_data()

            # 메트릭 정보 출력
            metrics = monitoring_data.get("metrics", {})
            total_metrics = metrics.get("total_metrics", {})

            self.stdout.write(f"📈 전체 검색 통계:")
            self.stdout.write(f"   총 검색 수: {total_metrics.get('search_count', 0)}")
            self.stdout.write(
                f"   평균 응답 시간: {total_metrics.get('avg_response_time', 0):.3f}초"
            )

            # 검색 유형별 통계
            search_types = total_metrics.get("search_types", {})
            if search_types:
                self.stdout.write(f"   검색 유형별 분포:")
                for search_type, count in search_types.items():
                    self.stdout.write(f"     {search_type}: {count}회")

            # 카테고리별 통계
            categories = total_metrics.get("categories", {})
            if categories:
                self.stdout.write(f"   카테고리별 분포:")
                for category, count in categories.items():
                    self.stdout.write(f"     {category}: {count}회")

            # 성능 요약
            performance_summary = monitoring_data.get("performance_summary", {})
            if "period" in performance_summary:
                self.stdout.write(f"\n📊 {performance_summary['period']} 성능 요약:")
                self.stdout.write(
                    f"   총 검색 수: {performance_summary.get('total_searches', 0)}"
                )
                self.stdout.write(
                    f"   평균 응답 시간: {performance_summary.get('avg_response_time', 0):.3f}초"
                )
                self.stdout.write(
                    f"   평균 결과 수: {performance_summary.get('avg_result_count', 0):.1f}"
                )
                self.stdout.write(
                    f"   평균 검색 점수: {performance_summary.get('avg_search_score', 0):.3f}"
                )

            # 권장사항
            recommendations = monitoring_data.get("recommendations", [])
            if recommendations:
                self.stdout.write(f"\n💡 검색 개선 권장사항:")
                for i, recommendation in enumerate(recommendations, 1):
                    self.stdout.write(f"   {i}. {recommendation}")

            # 성능 트렌드
            performance_trends = metrics.get("performance_trends", {})
            if "trend" in performance_trends:
                self.stdout.write(f"\n📈 성능 트렌드:")
                self.stdout.write(
                    f"   최근 평균 응답 시간: {performance_trends.get('recent_avg_response_time', 0):.3f}초"
                )
                self.stdout.write(
                    f"   트렌드: {performance_trends.get('trend', 'N/A')}"
                )
                improvement = performance_trends.get("improvement_percentage", 0)
                if improvement != 0:
                    self.stdout.write(f"   개선률: {improvement:.1f}%")

            # 검색 효율성
            search_efficiency = metrics.get("search_efficiency", {})
            overall_efficiency = search_efficiency.get("overall_efficiency", {})
            if overall_efficiency:
                self.stdout.write(f"\n⚡ 검색 효율성:")
                self.stdout.write(
                    f"   전체 평균 응답 시간: {overall_efficiency.get('avg_response_time', 0):.3f}초"
                )
                self.stdout.write(
                    f"   전체 평균 점수: {overall_efficiency.get('avg_score', 0):.3f}"
                )
                self.stdout.write(
                    f"   총 검색 수: {overall_efficiency.get('total_searches', 0)}"
                )

            self.stdout.write(self.style.SUCCESS("✅ 검색 메트릭 테스트 완료"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 메트릭 테스트 실패: {str(e)}"))
            logger.error(f"검색 메트릭 테스트 실패: {e}")

    def _test_integration(self, enhanced_search, performance_monitor):
        """통합 테스트"""
        self.stdout.write("\n🔄 향상된 검색 시스템 통합 테스트 시작...")

        try:
            # 복합 검색 시나리오
            complex_query = "자동차보험에서 무면허운전 사고 시 보험금 지급 조건"

            self.stdout.write(f"복합 쿼리: {complex_query}")

            # 성능 모니터링 시작
            performance_monitor.start_search(complex_query, "integrated")

            # 향상된 검색 수행
            search_results = enhanced_search.enhanced_search(
                query=complex_query, use_metadata=True
            )

            # 성능 모니터링 종료
            performance_monitor.end_search(search_results)

            # 결과 분석
            self.stdout.write(f"통합 검색 결과: {len(search_results)}개")

            if search_results:
                # 상위 결과 상세 분석
                top_result = search_results[0]
                metadata = top_result.get("metadata", {})

                self.stdout.write(f"최고 점수 결과:")
                self.stdout.write(f"  - 점수: {top_result.get('final_score', 0):.3f}")
                self.stdout.write(f"  - 제목: {metadata.get('title', 'N/A')}")
                self.stdout.write(f"  - 카테고리: {metadata.get('category', 'N/A')}")
                self.stdout.write(
                    f"  - 조문번호: {metadata.get('article_number', 'N/A')}"
                )

                # 컨텍스트 구축 테스트
                context = enhanced_search.build_enhanced_context(search_results[:3])
                self.stdout.write(f"컨텍스트 길이: {len(context)}자")

            # 검색 통계
            stats = enhanced_search.get_search_statistics(search_results)
            self.stdout.write(f"검색 통계: {stats}")

            self.stdout.write(self.style.SUCCESS("✅ 통합 테스트 완료"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 통합 테스트 실패: {str(e)}"))
            logger.error(f"통합 테스트 실패: {e}")
