import re
import logging
from typing import Dict, List, Optional, Tuple
from django.db.models import Q
from .models import DocumentChunk, InsuranceCompany

logger = logging.getLogger(__name__)


class ContactInfoService:
    """
    보험사별 연락처 정보를 체계적으로 관리하고 검색하는 서비스
    """
    
    def __init__(self):
        # 보험사별 연락처 정보 (정규화된 형태)
        self.contact_info = {
            "DB손해보험": {
                "name": "DB손해보험",
                "phone": "1588-0100",
                "description": "사고접수, 보험처리 등 보험계약 관련 문의",
                "source": "DB손해보험-프로미카개인용자동차보험약관"
            },
            "한화손해보험": {
                "name": "한화손해보험", 
                "phone": "1566-8000",
                "description": "고객상담센터",
                "source": "한화 개인용 자동차보험 약관"
            },
            "현대해상화재": {
                "name": "현대해상화재",
                "phone": "1588-5656", 
                "description": "고객상담센터",
                "source": "검색 결과에서 확인"
            },
            "메리츠화재": {
                "name": "메리츠화재",
                "phone": "1566-7711",
                "description": "고객상담센터", 
                "source": "검색 결과에서 확인"
            },
            "롯데손해보험": {
                "name": "롯데손해보험",
                "phone": "1588-0100",  # DB손해보험과 동일 (확인 필요)
                "description": "고객상담센터",
                "source": "검색 결과에서 확인"
            },
            "금융감독원": {
                "name": "금융감독원",
                "phone": "1332",
                "description": "보험모집질서 위반행위 신고센터",
                "source": "각 보험사 약관"
            }
        }
        
        # 전화번호 패턴
        self.phone_patterns = [
            r'(\d{3,4}-\d{3,4})',  # 1588-0100, 1566-8000 등
            r'(\d{4})',  # 1332 등
        ]
        
        # 보험사명 매칭 패턴
        self.company_patterns = {
            r'DB손해보험|프로미카': 'DB손해보험',
            r'한화손해보험|한화': '한화손해보험', 
            r'현대해상화재|현대해상': '현대해상화재',
            r'메리츠화재|메리츠': '메리츠화재',
            r'롯데손해보험|롯데': '롯데손해보험',
            r'금융감독원|감독원': '금융감독원'
        }

    def extract_contact_info_from_chunks(self) -> Dict[str, List[Dict]]:
        """
        문서 청크에서 연락처 정보를 추출하여 정리
        """
        contact_data = {}
        
        # 전화번호가 포함된 청크 검색
        phone_chunks = DocumentChunk.objects.filter(
            Q(chunk_text__icontains='전화') | 
            Q(chunk_text__icontains='1588') |
            Q(chunk_text__icontains='1566') |
            Q(chunk_text__icontains='1332')
        )
        
        for chunk in phone_chunks:
            chunk_text = chunk.chunk_text
            
            # 전화번호 추출
            phone_numbers = []
            for pattern in self.phone_patterns:
                matches = re.findall(pattern, chunk_text)
                phone_numbers.extend(matches)
            
            if phone_numbers:
                # 보험사명 추출
                company_name = self._extract_company_name(chunk_text)
                
                if company_name:
                    if company_name not in contact_data:
                        contact_data[company_name] = []
                    
                    contact_data[company_name].append({
                        'phone_numbers': phone_numbers,
                        'context': chunk_text[:200] + '...',
                        'document_title': chunk.document.title,
                        'chunk_id': chunk.id
                    })
        
        return contact_data

    def _extract_company_name(self, text: str) -> Optional[str]:
        """
        텍스트에서 보험사명 추출
        """
        for pattern, company in self.company_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return company
        return None

    def get_contact_info(self, company_name: str = None) -> Dict:
        """
        특정 보험사 또는 전체 보험사의 연락처 정보 반환
        """
        if company_name:
            # 특정 보험사 검색
            for pattern, company in self.company_patterns.items():
                if re.search(pattern, company_name, re.IGNORECASE):
                    return self.contact_info.get(company, {})
            return {}
        else:
            # 전체 보험사 정보 반환
            return self.contact_info

    def search_contact_info(self, query: str) -> List[Dict]:
        """
        질문에 맞는 연락처 정보 검색
        """
        results = []
        query_lower = query.lower()
        
        # 연락처 관련 키워드 확인
        contact_keywords = ['연락처', '전화번호', '고객센터', '상담', '문의']
        is_contact_query = any(keyword in query_lower for keyword in contact_keywords)
        
        if not is_contact_query:
            return results
        
        # 보험사명 추출
        target_company = None
        for pattern, company in self.company_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                target_company = company
                break
        
        if target_company:
            # 특정 보험사 연락처
            info = self.contact_info.get(target_company)
            if info:
                results.append({
                    'company': target_company,
                    'info': info,
                    'relevance_score': 1.0
                })
        else:
            # 전체 보험사 연락처
            for company, info in self.contact_info.items():
                if company != '금융감독원':  # 일반 보험사만
                    results.append({
                        'company': company,
                        'info': info,
                        'relevance_score': 0.8
                    })
        
        return results

    def format_contact_response(self, contact_results: List[Dict]) -> str:
        """
        연락처 정보를 사용자 친화적인 형태로 포맷팅
        """
        if not contact_results:
            return "죄송합니다. 해당 보험사의 연락처 정보를 찾을 수 없습니다."
        
        response_parts = []
        
        if len(contact_results) == 1:
            # 단일 보험사
            result = contact_results[0]
            info = result['info']
            response_parts.append(f"{info['name']}에 문의하고 싶으신 경우:")
            response_parts.append(f"- 전화: {info['phone']}")
            if info.get('description'):
                response_parts.append(f"- 문의내용: {info['description']}")
        else:
            # 여러 보험사
            response_parts.append("각 보험사별 문의 전화번호는 다음과 같습니다:")
            for i, result in enumerate(contact_results, 1):
                info = result['info']
                response_parts.append(f"{i}. {info['name']}: {info['phone']}")
        
        response_parts.append("\n추가로 궁금하신 점이나 다른 문의사항이 있으시면 언제든지 말씀해 주세요!")
        
        return "\n".join(response_parts)

    def update_contact_info_from_documents(self):
        """
        문서에서 연락처 정보를 추출하여 업데이트
        """
        extracted_data = self.extract_contact_info_from_chunks()
        logger.info(f"문서에서 추출된 연락처 정보: {extracted_data}")
        
        # 추출된 정보로 contact_info 업데이트
        for company, data_list in extracted_data.items():
            if data_list:
                # 가장 자주 나오는 전화번호 선택
                phone_counts = {}
                for data in data_list:
                    for phone in data['phone_numbers']:
                        phone_counts[phone] = phone_counts.get(phone, 0) + 1
                
                if phone_counts:
                    most_common_phone = max(phone_counts, key=phone_counts.get)
                    
                    if company not in self.contact_info:
                        self.contact_info[company] = {
                            'name': company,
                            'phone': most_common_phone,
                            'description': '고객상담센터',
                            'source': '문서에서 추출'
                        }
                    else:
                        self.contact_info[company]['phone'] = most_common_phone
                        self.contact_info[company]['source'] = '문서에서 추출'
        
        logger.info(f"업데이트된 연락처 정보: {self.contact_info}")
