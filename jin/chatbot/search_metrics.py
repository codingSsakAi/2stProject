import logging
import time
from typing import List, Dict, Any, Optional
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from .models import DocumentChunk

logger = logging.getLogger(__name__)


class SearchMetrics:
    """검색 성능 메트릭 시스템"""

    def __init__(self):
        self.metrics = {
            "search_count": 0,
            "total_response_time": 0.0,
            "avg_response_time": 0.0,
            "search_types": {},
            "categories": {},
            "query_patterns": {},
            "performance_history": []
        }

    def record_search(
        self, 
        query: str, 
        search_type: str, 
        response_time: float, 
        result_count: int,
        search_results: List[Dict[str, Any]] = None
    ):
        """검색 기록"""
        try:
            # 기본 메트릭 업데이트
            self.metrics["search_count"] += 1
            self.metrics["total_response_time"] += response_time
            self.metrics["avg_response_time"] = (
                self.metrics["total_response_time"] / self.metrics["search_count"]
            )

            # 검색 유형 통계
            self.metrics["search_types"][search_type] = (
                self.metrics["search_types"].get(search_type, 0) + 1
            )

            # 성능 히스토리 기록
            performance_record = {
                "timestamp": timezone.now(),
                "query": query,
                "search_type": search_type,
                "response_time": response_time,
                "result_count": result_count,
                "avg_score": 0.0
            }

            # 검색 결과 분석
            if search_results:
                performance_record["avg_score"] = self._calculate_avg_score(search_results)
                self._analyze_search_results(search_results)

            self.metrics["performance_history"].append(performance_record)

            # 쿼리 패턴 분석
            self._analyze_query_pattern(query)

            logger.info(f"검색 메트릭 기록: {search_type}, {response_time:.3f}초, {result_count}개 결과")

        except Exception as e:
            logger.error(f"검색 메트릭 기록 오류: {e}")

    def _calculate_avg_score(self, search_results: List[Dict[str, Any]]) -> float:
        """평균 점수 계산"""
        try:
            if not search_results:
                return 0.0
            
            total_score = sum(result.get("final_score", 0) for result in search_results)
            return total_score / len(search_results)
            
        except Exception as e:
            logger.error(f"평균 점수 계산 오류: {e}")
            return 0.0

    def _analyze_search_results(self, search_results: List[Dict[str, Any]]):
        """검색 결과 분석"""
        try:
            for result in search_results:
                metadata = result.get("metadata", {})
                category = metadata.get("category", "기타")
                
                # 카테고리 통계
                self.metrics["categories"][category] = (
                    self.metrics["categories"].get(category, 0) + 1
                )
                
        except Exception as e:
            logger.error(f"검색 결과 분석 오류: {e}")

    def _analyze_query_pattern(self, query: str):
        """쿼리 패턴 분석"""
        try:
            # 쿼리 길이별 패턴
            query_length = len(query)
            if query_length <= 10:
                pattern = "짧은_쿼리"
            elif query_length <= 30:
                pattern = "중간_쿼리"
            else:
                pattern = "긴_쿼리"
            
            self.metrics["query_patterns"][pattern] = (
                self.metrics["query_patterns"].get(pattern, 0) + 1
            )
            
        except Exception as e:
            logger.error(f"쿼리 패턴 분석 오류: {e}")

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """성능 요약 정보"""
        try:
            cutoff_time = timezone.now() - timedelta(hours=hours)
            
            # 최근 검색 기록 필터링
            recent_searches = [
                record for record in self.metrics["performance_history"]
                if record["timestamp"] >= cutoff_time
            ]
            
            if not recent_searches:
                return {"message": f"최근 {hours}시간 동안 검색 기록이 없습니다."}
            
            # 성능 통계 계산
            response_times = [record["response_time"] for record in recent_searches]
            result_counts = [record["result_count"] for record in recent_searches]
            avg_scores = [record["avg_score"] for record in recent_searches]
            
            summary = {
                "period": f"최근 {hours}시간",
                "total_searches": len(recent_searches),
                "avg_response_time": sum(response_times) / len(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "avg_result_count": sum(result_counts) / len(result_counts),
                "avg_search_score": sum(avg_scores) / len(avg_scores),
                "search_types": {},
                "top_categories": {},
                "query_patterns": {}
            }
            
            # 검색 유형별 통계
            for record in recent_searches:
                search_type = record["search_type"]
                summary["search_types"][search_type] = (
                    summary["search_types"].get(search_type, 0) + 1
                )
            
            # 상위 카테고리
            category_counts = {}
            for record in recent_searches:
                # 카테고리 정보는 별도로 저장되어야 함
                pass
            
            # 쿼리 패턴
            for record in recent_searches:
                query_length = len(record["query"])
                if query_length <= 10:
                    pattern = "짧은_쿼리"
                elif query_length <= 30:
                    pattern = "중간_쿼리"
                else:
                    pattern = "긴_쿼리"
                
                summary["query_patterns"][pattern] = (
                    summary["query_patterns"].get(pattern, 0) + 1
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"성능 요약 생성 오류: {e}")
            return {"error": str(e)}

    def get_search_analytics(self) -> Dict[str, Any]:
        """검색 분석 정보"""
        try:
            analytics = {
                "total_metrics": self.metrics.copy(),
                "performance_trends": self._calculate_performance_trends(),
                "search_efficiency": self._calculate_search_efficiency(),
                "recommendations": self._generate_recommendations()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"검색 분석 생성 오류: {e}")
            return {"error": str(e)}

    def _calculate_performance_trends(self) -> Dict[str, Any]:
        """성능 트렌드 계산"""
        try:
            if len(self.metrics["performance_history"]) < 2:
                return {"message": "트렌드 분석을 위한 충분한 데이터가 없습니다."}
            
            # 최근 10개 검색의 평균 응답 시간
            recent_searches = self.metrics["performance_history"][-10:]
            recent_avg = sum(record["response_time"] for record in recent_searches) / len(recent_searches)
            
            # 이전 10개 검색의 평균 응답 시간
            if len(self.metrics["performance_history"]) >= 20:
                previous_searches = self.metrics["performance_history"][-20:-10]
                previous_avg = sum(record["response_time"] for record in previous_searches) / len(previous_searches)
                
                trend = "개선" if recent_avg < previous_avg else "악화" if recent_avg > previous_avg else "유지"
                improvement = ((previous_avg - recent_avg) / previous_avg) * 100 if previous_avg > 0 else 0
            else:
                trend = "분석 불가"
                improvement = 0
            
            return {
                "recent_avg_response_time": recent_avg,
                "trend": trend,
                "improvement_percentage": improvement
            }
            
        except Exception as e:
            logger.error(f"성능 트렌드 계산 오류: {e}")
            return {"error": str(e)}

    def _calculate_search_efficiency(self) -> Dict[str, Any]:
        """검색 효율성 계산"""
        try:
            if not self.metrics["performance_history"]:
                return {"message": "검색 기록이 없습니다."}
            
            # 응답 시간 효율성
            response_times = [record["response_time"] for record in self.metrics["performance_history"]]
            avg_response_time = sum(response_times) / len(response_times)
            
            # 결과 품질 효율성
            avg_scores = [record["avg_score"] for record in self.metrics["performance_history"] if record["avg_score"] > 0]
            avg_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
            
            # 검색 유형별 효율성
            type_efficiency = {}
            for search_type in self.metrics["search_types"]:
                type_searches = [
                    record for record in self.metrics["performance_history"]
                    if record["search_type"] == search_type
                ]
                if type_searches:
                    type_avg_time = sum(record["response_time"] for record in type_searches) / len(type_searches)
                    type_avg_score = sum(record["avg_score"] for record in type_searches) / len(type_searches)
                    type_efficiency[search_type] = {
                        "avg_response_time": type_avg_time,
                        "avg_score": type_avg_score,
                        "count": len(type_searches)
                    }
            
            return {
                "overall_efficiency": {
                    "avg_response_time": avg_response_time,
                    "avg_score": avg_score,
                    "total_searches": self.metrics["search_count"]
                },
                "type_efficiency": type_efficiency
            }
            
        except Exception as e:
            logger.error(f"검색 효율성 계산 오류: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self) -> List[str]:
        """검색 개선 권장사항 생성"""
        try:
            recommendations = []
            
            # 응답 시간 기반 권장사항
            if self.metrics["avg_response_time"] > 2.0:
                recommendations.append("검색 응답 시간이 느립니다. 인덱스 최적화를 고려하세요.")
            
            # 검색 유형 기반 권장사항
            if "vector" in self.metrics["search_types"] and "keyword" in self.metrics["search_types"]:
                vector_ratio = self.metrics["search_types"]["vector"] / self.metrics["search_count"]
                if vector_ratio < 0.3:
                    recommendations.append("벡터 검색 사용률이 낮습니다. 하이브리드 검색을 활성화하세요.")
            
            # 카테고리 기반 권장사항
            if self.metrics["categories"]:
                top_category = max(self.metrics["categories"], key=self.metrics["categories"].get)
                recommendations.append(f"가장 많이 검색되는 카테고리는 '{top_category}'입니다.")
            
            # 쿼리 패턴 기반 권장사항
            if "짧은_쿼리" in self.metrics["query_patterns"]:
                short_query_ratio = self.metrics["query_patterns"]["짧은_쿼리"] / self.metrics["search_count"]
                if short_query_ratio > 0.7:
                    recommendations.append("짧은 쿼리가 많습니다. 키워드 확장 기능을 활용하세요.")
            
            return recommendations if recommendations else ["현재 검색 성능이 양호합니다."]
            
        except Exception as e:
            logger.error(f"권장사항 생성 오류: {e}")
            return ["권장사항 생성 중 오류가 발생했습니다."]

    def reset_metrics(self):
        """메트릭 초기화"""
        try:
            self.metrics = {
                "search_count": 0,
                "total_response_time": 0.0,
                "avg_response_time": 0.0,
                "search_types": {},
                "categories": {},
                "query_patterns": {},
                "performance_history": []
            }
            logger.info("검색 메트릭이 초기화되었습니다.")
            
        except Exception as e:
            logger.error(f"메트릭 초기화 오류: {e}")

    def export_metrics(self, format: str = "json") -> str:
        """메트릭 내보내기"""
        try:
            import json
            
            if format.lower() == "json":
                return json.dumps(self.metrics, default=str, indent=2, ensure_ascii=False)
            else:
                return str(self.metrics)
                
        except Exception as e:
            logger.error(f"메트릭 내보내기 오류: {e}")
            return f"내보내기 오류: {str(e)}"


class SearchPerformanceMonitor:
    """검색 성능 모니터링 클래스"""

    def __init__(self):
        self.metrics = SearchMetrics()
        self.start_time = None

    def start_search(self, query: str, search_type: str = "hybrid"):
        """검색 시작"""
        self.start_time = time.time()
        self.current_query = query
        self.current_search_type = search_type

    def end_search(self, search_results: List[Dict[str, Any]] = None):
        """검색 종료"""
        if self.start_time is None:
            logger.warning("검색이 시작되지 않았습니다.")
            return
        
        response_time = time.time() - self.start_time
        result_count = len(search_results) if search_results else 0
        
        self.metrics.record_search(
            query=self.current_query,
            search_type=self.current_search_type,
            response_time=response_time,
            result_count=result_count,
            search_results=search_results
        )
        
        self.start_time = None
        self.current_query = None
        self.current_search_type = None

    def get_monitoring_data(self) -> Dict[str, Any]:
        """모니터링 데이터 반환"""
        return {
            "metrics": self.metrics.get_search_analytics(),
            "performance_summary": self.metrics.get_performance_summary(),
            "recommendations": self.metrics._generate_recommendations()
        }
