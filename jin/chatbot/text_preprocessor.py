import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """텍스트 전처리 및 정제 클래스"""

    def __init__(self):
        self.cleaning_patterns = [
            # 불필요한 공백 제거
            (r'\s+', ' '),
            # 특수문자 제거 (한글, 영문, 숫자, 공백, 마침표, 콤마, 콜론만 유지)
            (r'[^가-힣a-zA-Z0-9\s.,:]', ''),
            # 연속된 마침표 제거
            (r'\.{2,}', '.'),
            # 연속된 콤마 제거
            (r',{2,}', ','),
        ]

    def clean_text(self, text: str) -> str:
        """텍스트 정제 (강화된 버전)"""
        if not text:
            return ""
        
        try:
            cleaned_text = text
            
            # 마크다운 문법 제거
            cleaned_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_text)  # **볼드** 제거
            cleaned_text = re.sub(r'\*([^*]+)\*', r'\1', cleaned_text)      # *이탤릭* 제거
            cleaned_text = re.sub(r'#+\s*', '', cleaned_text)               # # 헤더 제거
            cleaned_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned_text)  # [링크](url) 제거
            cleaned_text = re.sub(r'`([^`]+)`', r'\1', cleaned_text)        # `코드` 제거
            
            # 개행문자 제거
            cleaned_text = cleaned_text.replace('\n', ' ')
            cleaned_text = cleaned_text.replace('\r', ' ')
            cleaned_text = cleaned_text.replace('\t', ' ')
            
            # 한글 사이 불필요한 공백 제거
            cleaned_text = re.sub(r'([가-힣])\s+([가-힣])', r'\1\2', cleaned_text)
            
            # 정규표현식 패턴 적용
            for pattern, replacement in self.cleaning_patterns:
                cleaned_text = re.sub(pattern, replacement, cleaned_text)
            
            # 중복 텍스트 제거 (동일한 문장이 연속으로 나오는 경우)
            sentences = cleaned_text.split('.')
            cleaned_sentences = []
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if sentence and (i == 0 or sentence != sentences[i-1].strip()):
                    cleaned_sentences.append(sentence)
            cleaned_text = '. '.join(cleaned_sentences)
            
            # 앞뒤 공백 제거
            cleaned_text = cleaned_text.strip()
            
            logger.info(f"텍스트 정제 완료: {len(text)} -> {len(cleaned_text)} 문자")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"텍스트 정제 중 오류: {e}")
            return text

    def extract_article_numbers(self, text: str) -> Dict[str, Any]:
        """조문번호 추출 (강화된 버전)"""
        article_info = {
            'article_number': None,
            'section_number': None,
            'subsection_number': None,
            'article_hierarchy': None
        }
        
        try:
            # 조문번호 패턴들 (더 포괄적)
            article_patterns = [
                r'제(\d+)조',                    # 제1조, 제2조
                r'제(\d+)조의(\d+)',             # 제1조의2
                r'제(\d+)조\((\d+)\)',           # 제1조(2)
                r'제(\d+)조\s*(\d+)항',          # 제1조 2항
                r'제(\d+)조\s*(\d+)호',          # 제1조 2호
                r'(\d+)조',                      # 1조
                r'(\d+)\.',                      # 1., 2.
                r'\((\d+)\)',                    # (1), (2)
                r'(\d+)항',                      # 1항, 2항
                r'(\d+)호',                      # 1호, 2호
            ]
            
            # 조항번호 패턴들 (한글 원문자 포함)
            section_patterns = [
                r'①', r'②', r'③', r'④', r'⑤', r'⑥', r'⑦', r'⑧', r'⑨', r'⑩',
                r'⑴', r'⑵', r'⑶', r'⑷', r'⑸', r'⑹', r'⑺', r'⑻', r'⑼', r'⑽',
                r'㈀', r'㈁', r'㈂', r'㈃', r'㈄', r'㈅', r'㈆', r'㈇', r'㈈', r'㈉'
            ]
            
            # 조문번호 찾기
            for pattern in article_patterns:
                match = re.search(pattern, text)
                if match:
                    if len(match.groups()) == 1:
                        article_info['article_number'] = int(match.group(1))
                    elif len(match.groups()) == 2:
                        article_info['article_number'] = int(match.group(1))
                        article_info['section_number'] = int(match.group(2))
                    break
            
            # 조항번호 찾기 (한글 원문자)
            for i, pattern in enumerate(section_patterns):
                if pattern in text:
                    article_info['section_number'] = i + 1
                    break
            
            # 항번호 찾기 (조문번호가 있는 경우에만)
            if article_info['article_number']:
                # 항번호 패턴들
                item_patterns = [
                    r'(\d+)\.\s*([가-힣])',      # 1. 가나다
                    r'(\d+)\)\s*([가-힣])',      # 1) 가나다
                    r'(\d+)\s*([가-힣])',        # 1 가나다
                ]
                
                for pattern in item_patterns:
                    match = re.search(pattern, text)
                    if match:
                        article_info['subsection_number'] = int(match.group(1))
                        break
            
            # 계층 구조 생성
            hierarchy_parts = []
            if article_info['article_number']:
                hierarchy_parts.append(str(article_info['article_number']))
            if article_info['section_number']:
                hierarchy_parts.append(str(article_info['section_number']))
            if article_info['subsection_number']:
                hierarchy_parts.append(str(article_info['subsection_number']))
            
            if hierarchy_parts:
                article_info['article_hierarchy'] = '.'.join(hierarchy_parts)
            
            logger.info(f"조문번호 추출 완료: {article_info}")
            return article_info
            
        except Exception as e:
            logger.error(f"조문번호 추출 중 오류: {e}")
            return article_info

    def extract_page_info(self, text: str, total_pages: int = None) -> Dict[str, Any]:
        """페이지 정보 추출"""
        page_info = {
            'page_number': None,
            'total_pages': total_pages,
            'page_type': 'content'
        }
        
        try:
            # 페이지 번호 패턴들
            page_patterns = [
                r'(\d+)페이지',
                r'페이지\s*(\d+)',
                r'p\.\s*(\d+)',
                r'page\s*(\d+)',
            ]
            
            for pattern in page_patterns:
                match = re.search(pattern, text)
                if match:
                    page_info['page_number'] = int(match.group(1))
                    break
            
            # 페이지 타입 판별
            if any(keyword in text for keyword in ['목차', '차례', 'index']):
                page_info['page_type'] = 'toc'
            elif any(keyword in text for keyword in ['부칙', '시행규칙', '부록']):
                page_info['page_type'] = 'appendix'
            
            logger.info(f"페이지 정보 추출 완료: {page_info}")
            return page_info
            
        except Exception as e:
            logger.error(f"페이지 정보 추출 중 오류: {e}")
            return page_info

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """키워드 추출 (기본 규칙 기반)"""
        try:
            # 보험 관련 키워드 패턴
            insurance_keywords = [
                '보험료', '보험금', '면책', '배상', '사고', '계약', '가입', '해지',
                '갱신', '변경', '환급', '할인', '공제', '특약', '부가보장',
                '자동차', '생명', '손해', '건강', '연금', '여행', '재산',
                '운전자', '피보험자', '보험자', '수익자', '계약자'
            ]
            
            # 텍스트에서 키워드 찾기
            found_keywords = []
            for keyword in insurance_keywords:
                if keyword in text:
                    found_keywords.append(keyword)
            
            # 빈도순으로 정렬하고 상위 키워드 반환
            found_keywords = found_keywords[:max_keywords]
            
            logger.info(f"키워드 추출 완료: {found_keywords}")
            return found_keywords
            
        except Exception as e:
            logger.error(f"키워드 추출 중 오류: {e}")
            return []

    def generate_summary(self, text: str, max_length: int = 100) -> str:
        """텍스트 요약 생성 (기본 규칙 기반)"""
        try:
            if not text:
                return ""
            
            # 첫 번째 문장 추출
            sentences = re.split(r'[.!?]', text)
            first_sentence = sentences[0].strip() if sentences else ""
            
            # 길이 제한
            if len(first_sentence) > max_length:
                summary = first_sentence[:max_length] + "..."
            else:
                summary = first_sentence
            
            logger.info(f"요약 생성 완료: {len(summary)} 문자")
            return summary
            
        except Exception as e:
            logger.error(f"요약 생성 중 오류: {e}")
            return ""

    def process_chunk(self, chunk_text: str, chunk_index: int, document_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """청크별 통합 전처리"""
        try:
            # 텍스트 정제
            cleaned_text = self.clean_text(chunk_text)
            
            # 메타데이터 추출
            article_info = self.extract_article_numbers(cleaned_text)
            page_info = self.extract_page_info(cleaned_text, document_info.get('total_pages') if document_info else None)
            keywords = self.extract_keywords(cleaned_text)
            summary = self.generate_summary(cleaned_text)
            
            # 통합 메타데이터
            metadata = {
                'chunk_id': f"chunk_{chunk_index:03d}",
                'chunk_index': chunk_index,
                'content_length': len(cleaned_text),
                'cleaned_text': cleaned_text,
                'extraction_method': 'rule_based',
                'confidence_score': 0.8,  # 기본 신뢰도
                'review_status': 'pending',
                'metadata_version': '1.0',
                **article_info,
                **page_info,
                'keywords': keywords,
                'summary': summary
            }
            
            logger.info(f"청크 {chunk_index} 전처리 완료")
            return metadata
            
        except Exception as e:
            logger.error(f"청크 {chunk_index} 전처리 중 오류: {e}")
            return {
                'chunk_id': f"chunk_{chunk_index:03d}",
                'chunk_index': chunk_index,
                'content_length': len(chunk_text),
                'cleaned_text': chunk_text,
                'extraction_method': 'rule_based',
                'confidence_score': 0.0,
                'review_status': 'error',
                'metadata_version': '1.0'
            }
