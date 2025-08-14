import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    챗봇 응답 캐싱 서비스
    """
    
    def __init__(self):
        self.default_ttl = 3600  # 1시간 (초)
        self.contact_cache_ttl = 86400  # 24시간 (연락처 정보는 더 오래 캐시)
        self.frequent_queries_ttl = 7200  # 2시간 (자주 묻는 질문)
        
        # 자주 묻는 질문 패턴
        self.frequent_query_patterns = [
            r'연락처|전화번호|고객센터',
            r'보험료|요금|가격',
            r'가입|신청|계약',
            r'해지|취소|환급',
            r'사고|보상|청구',
            r'할인|혜택|프로모션'
        ]
        
        # 캐시 키 접두사
        self.cache_prefixes = {
            'chat_response': 'chat_response:',
            'contact_info': 'contact_info:',
            'frequent_query': 'frequent_query:',
            'search_result': 'search_result:'
        }

    def _generate_cache_key(self, query: str, prefix: str = 'chat_response') -> str:
        """
        쿼리를 기반으로 캐시 키 생성
        """
        # 쿼리 정규화 (공백 제거, 소문자 변환)
        normalized_query = ' '.join(query.lower().split())
        
        # SHA-256 해시 생성
        query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()[:16]
        
        return f"{self.cache_prefixes.get(prefix, 'cache:')}{query_hash}"

    def _is_frequent_query(self, query: str) -> bool:
        """
        자주 묻는 질문인지 확인
        """
        import re
        query_lower = query.lower()
        
        for pattern in self.frequent_query_patterns:
            if re.search(pattern, query_lower):
                return True
        return False

    def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """
        캐시된 응답 조회
        """
        try:
            # 연락처 관련 질문인지 확인
            if self._is_contact_query(query):
                cache_key = self._generate_cache_key(query, 'contact_info')
                ttl = self.contact_cache_ttl
            elif self._is_frequent_query(query):
                cache_key = self._generate_cache_key(query, 'frequent_query')
                ttl = self.frequent_queries_ttl
            else:
                cache_key = self._generate_cache_key(query, 'chat_response')
                ttl = self.default_ttl
            
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"캐시 히트: {query[:50]}...")
                return {
                    'response': cached_data['response'],
                    'metadata': cached_data.get('metadata', {}),
                    'cached_at': cached_data.get('cached_at'),
                    'ttl': ttl
                }
            
            logger.info(f"캐시 미스: {query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"캐시 조회 오류: {e}")
            return None

    def cache_response(self, query: str, response: Dict[str, Any]) -> bool:
        """
        응답을 캐시에 저장
        """
        try:
            # 연락처 관련 질문인지 확인
            if self._is_contact_query(query):
                cache_key = self._generate_cache_key(query, 'contact_info')
                ttl = self.contact_cache_ttl
            elif self._is_frequent_query(query):
                cache_key = self._generate_cache_key(query, 'frequent_query')
                ttl = self.frequent_queries_ttl
            else:
                cache_key = self._generate_cache_key(query, 'chat_response')
                ttl = self.default_ttl
            
            # 캐시 데이터 구성
            cache_data = {
                'response': response.get('answer', ''),
                'metadata': response.get('metadata', {}),
                'cached_at': datetime.now().isoformat(),
                'query': query[:100]  # 쿼리 일부 저장 (디버깅용)
            }
            
            # 캐시 저장
            cache.set(cache_key, cache_data, ttl)
            
            logger.info(f"응답 캐시 저장: {query[:50]}... (TTL: {ttl}초)")
            return True
            
        except Exception as e:
            logger.error(f"캐시 저장 오류: {e}")
            return False

    def _is_contact_query(self, query: str) -> bool:
        """
        연락처 관련 질문인지 확인
        """
        contact_keywords = ['연락처', '전화번호', '고객센터', '상담', '문의', '1588', '1566', '1332']
        query_lower = query.lower()
        
        return any(keyword in query_lower for keyword in contact_keywords)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보 반환
        """
        try:
            stats = {
                'total_keys': 0,
                'contact_cache_keys': 0,
                'frequent_query_keys': 0,
                'chat_response_keys': 0,
                'cache_size_mb': 0
            }
            
            # 캐시 키 패턴별 개수 계산 (Redis의 경우)
            if hasattr(cache, 'client') and hasattr(cache.client, 'keys'):
                try:
                    # Redis 키 패턴 검색
                    for prefix_name, prefix in self.cache_prefixes.items():
                        pattern = f"{prefix}*"
                        keys = cache.client.keys(pattern)
                        stats[f'{prefix_name}_keys'] = len(keys)
                        stats['total_keys'] += len(keys)
                except Exception as e:
                    logger.warning(f"캐시 통계 조회 실패: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"캐시 통계 조회 오류: {e}")
            return {}

    def clear_cache(self, pattern: str = None) -> bool:
        """
        캐시 삭제
        """
        try:
            if pattern:
                # 특정 패턴의 캐시만 삭제
                cache_key = self._generate_cache_key(pattern, 'chat_response')
                cache.delete(cache_key)
                logger.info(f"특정 캐시 삭제: {pattern}")
            else:
                # 전체 캐시 삭제
                cache.clear()
                logger.info("전체 캐시 삭제 완료")
            
            return True
            
        except Exception as e:
            logger.error(f"캐시 삭제 오류: {e}")
            return False

    def get_cache_info(self, query: str) -> Dict[str, Any]:
        """
        특정 쿼리의 캐시 정보 반환
        """
        try:
            cache_key = self._generate_cache_key(query)
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return {
                    'is_cached': True,
                    'cached_at': cached_data.get('cached_at'),
                    'ttl': self._get_cache_ttl(query),
                    'cache_key': cache_key
                }
            else:
                return {
                    'is_cached': False,
                    'cache_key': cache_key
                }
                
        except Exception as e:
            logger.error(f"캐시 정보 조회 오류: {e}")
            return {'is_cached': False, 'error': str(e)}

    def _get_cache_ttl(self, query: str) -> int:
        """
        쿼리에 따른 캐시 TTL 반환
        """
        if self._is_contact_query(query):
            return self.contact_cache_ttl
        elif self._is_frequent_query(query):
            return self.frequent_queries_ttl
        else:
            return self.default_ttl
