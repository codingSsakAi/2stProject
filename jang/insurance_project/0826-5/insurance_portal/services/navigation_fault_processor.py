# -*- coding: utf-8 -*-
# insurance_portal/services/navigation_fault_processor.py
# 목적: 네비게이션 방식으로 선택된 쿼리를 처리하여 과실비율 분석 결과 생성

import logging

logger = logging.getLogger(__name__)

def process_navigation_query(query, navigation_context):
    """
    네비게이션을 통해 선택된 쿼리를 처리하여 과실비율 분석 결과 생성
    
    Args:
        query (str): 조합된 쿼리 문자열 (예: "교차로 사고 > 신호등 교차로 > 직진 vs 좌회전 > 직진차 신호준수 - 좌회전차 신호위반")
        navigation_context (dict): 네비게이션 컨텍스트 정보
            {
                "path": ["교차로 사고", "신호등 교차로", "직진 vs 좌회전"],
                "selected_option": "직진차 신호준수 - 좌회전차 신호위반",
                "is_navigation_query": true
            }
    
    Returns:
        dict: 과실비율 분석 결과
        {
            "needs_more_input": false,
            "accident_description": "사고 설명",
            "base_fault": "기본 과실비율",
            "base_fault_description": "기본 과실비율 설명",
            "modification_factors": "수정 요소들",
            "modification_description": "수정 요소 설명", 
            "final_fault": "최종 과실비율",
            "legal_info": "관련 법규",
            "precedents": "관련 판례",
            "citations": [...]
        }
    """
    try:
        # 기존 fault_answerer 활용
        from .fault_answerer import answer_fault
        
        path = navigation_context.get('path', [])
        selected_option = navigation_context.get('selected_option', '')
        
        logger.info(f"[NAV-PROCESSOR] Processing navigation query: {query}")
        logger.info(f"[NAV-PROCESSOR] Path: {path}, Option: {selected_option}")
        
        # 키워드 추출 및 검색 쿼리 생성
        search_keywords = extract_search_keywords(path, selected_option)
        enhanced_query = build_enhanced_query(path, selected_option)
        
        logger.info(f"[NAV-PROCESSOR] Search keywords: {search_keywords}")
        logger.info(f"[NAV-PROCESSOR] Enhanced query: {enhanced_query}")
        
        # 네비게이션 컨텍스트를 포함한 대화 히스토리 생성
        conversation_history = [
            {
                "role": "user", 
                "content": f"네비게이션으로 선택한 사고 유형: {query}"
            }
        ]
        
        # 기존 fault_answerer 호출
        result = answer_fault(
            query=enhanced_query,
            conversation_history=conversation_history
        )
        
        # 네비게이션 쿼리는 항상 최종 결과를 반환해야 함
        if result.get('needs_more_input', False):
            logger.warning(f"[NAV-PROCESSOR] Navigation query returned needs_more_input, converting to final result")
            result = convert_to_final_result(result, query, path, selected_option)
        
        # 결과 후처리 - 6개 섹션 형태로 변환
        result = enhance_navigation_result(result, path, selected_option)
        
        logger.info(f"[NAV-PROCESSOR] Successfully processed navigation query")
        
        return result
        
    except Exception as e:
        logger.exception(f"[NAV-PROCESSOR] Error processing navigation query: {e}")
        
        # 에러 시 기본 응답 반환
        return create_fallback_result(query, path, selected_option)


def extract_search_keywords(path, selected_option):
    """
    네비게이션 경로와 선택 옵션에서 검색 키워드 추출
    
    Args:
        path (list): 네비게이션 경로
        selected_option (str): 선택된 옵션
    
    Returns:
        list: 검색 키워드 리스트
    """
    keywords = []
    
    # 경로에서 키워드 추출
    for item in path:
        # 특수 키워드 정리
        cleaned = item.replace('사고', '').replace('vs', '').strip()
        if cleaned:
            keywords.append(cleaned)
    
    # 선택 옵션에서 키워드 추출  
    if selected_option:
        # '-'로 구분된 부분들 처리
        parts = selected_option.split('-')
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                keywords.append(cleaned)
    
    # 중복 제거 및 정리
    unique_keywords = []
    for keyword in keywords:
        if keyword not in unique_keywords and len(keyword) > 1:
            unique_keywords.append(keyword)
    
    return unique_keywords


def build_enhanced_query(path, selected_option):
    """
    네비게이션 정보를 바탕으로 향상된 쿼리 생성
    
    Args:
        path (list): 네비게이션 경로
        selected_option (str): 선택된 옵션
    
    Returns:
        str: 향상된 검색 쿼리
    """
    # 기본 쿼리
    base_query = ' '.join(path)
    
    # 선택 옵션 추가
    if selected_option:
        base_query += f" {selected_option}"
    
    # 과실비율 관련 키워드 추가
    enhanced_query = f"{base_query} 과실비율 과실 비율 책임"
    
    return enhanced_query


def convert_to_final_result(partial_result, query, path, selected_option):
    """
    부분 결과를 최종 결과로 변환
    
    Args:
        partial_result (dict): 부분 결과
        query (str): 원본 쿼리
        path (list): 네비게이션 경로
        selected_option (str): 선택된 옵션
    
    Returns:
        dict: 최종 결과
    """
    # 기본 템플릿 사용
    accident_type = ' > '.join(path) if path else "교통사고"
    
    final_result = {
        "needs_more_input": False,
        "accident_description": f"선택하신 사고 유형: {query}",
        "base_fault": "구체적 상황에 따라 결정",
        "base_fault_description": f"{accident_type} 상황에서의 기본 과실비율은 신호 준수 여부, 우선권, 안전 의무 등에 따라 결정됩니다.",
        "modification_factors": "가감 요소들",
        "modification_description": "속도위반(+10~20%), 음주운전(+20~30%), 안전확인 의무 위반(+10%), 기타 도로교통법 위반 사항들이 과실비율에 영향을 줍니다.",
        "final_fault": "상세 상황 검토 필요",
        "legal_info": "도로교통법, 민법 제750조(불법행위), 자동차손해배상보장법 등이 적용됩니다.",
        "precedents": "구체적인 사고 경위와 증거에 따라 법원의 과실 인정 비율이 달라질 수 있습니다.",
        "citations": []
    }
    
    # 부분 결과에서 사용 가능한 정보 병합
    if partial_result.get('summary'):
        final_result["base_fault_description"] = partial_result['summary']
    
    if partial_result.get('final_answer'):
        final_result["modification_description"] = partial_result['final_answer']
    
    return final_result


def enhance_navigation_result(result, path, selected_option):
    """
    네비게이션 정보를 활용하여 결과를 6개 섹션 형태로 향상
    
    Args:
        result (dict): 기본 결과
        path (list): 네비게이션 경로  
        selected_option (str): 선택된 옵션
    
    Returns:
        dict: 향상된 결과
    """
    # 6개 섹션에 맞게 기존 결과 재구성
    enhanced_result = {
        "needs_more_input": False,
        
        # 1. 사고 설명
        "accident_description": result.get('accident_description') or f"사고 유형: {' > '.join(path)}\n상세 상황: {selected_option}",
        
        # 2. 기본과실 + 기본과실 설명  
        "base_fault": extract_base_fault_from_result(result, path),
        "base_fault_description": extract_base_fault_description_from_result(result, path, selected_option),
        
        # 3. 수정항목 + 수정항목 설명
        "modification_factors": extract_modification_factors_from_result(result),
        "modification_description": extract_modification_description_from_result(result),
        
        # 4. 수정된과실
        "final_fault": extract_final_fault_from_result(result),
        
        # 5. 법규
        "legal_info": extract_legal_info_from_result(result),
        
        # 6. 판례
        "precedents": extract_precedents_from_result(result),
        
        # 기타
        "citations": result.get('citations', []),
        "navigation_context": {
            'category_path': path,
            'selected_scenario': selected_option,
            'search_completed': True
        }
    }
    
    return enhanced_result


def extract_base_fault_from_result(result, path):
    """기존 결과에서 기본과실 추출"""
    # final_answer에서 비율 패턴 찾기
    import re
    
    final_answer = result.get('final_answer', '')
    ratio_patterns = [
        r'(\d+:\d+)',  # 70:30 형태
        r'(\d+%\s*:\s*\d+%)',  # 70% : 30% 형태
        r'(\d+\s*대\s*\d+)',  # 7대3 형태
    ]
    
    for pattern in ratio_patterns:
        match = re.search(pattern, final_answer)
        if match:
            return match.group(1)
    
    # 패턴을 찾지 못한 경우 사고 유형별 기본값 추정
    if any('교차로' in p for p in path):
        return "상황별 차등적용"
    elif any('추돌' in p for p in path):
        return "후방차량 100% (일반적)"
    elif any('차로변경' in p for p in path):
        return "차로변경차량 80~100%"
    else:
        return "상황에 따라 결정"


def extract_base_fault_description_from_result(result, path, selected_option):
    """기존 결과에서 기본과실 설명 추출 및 보강"""
    base_description = result.get('final_answer', '')
    
    # 네비게이션 정보로 설명 보강
    accident_context = ' > '.join(path) if path else "해당 사고"
    
    enhanced = f"{accident_context} 상황에서 선택하신 '{selected_option}' 시나리오의 기본 과실비율입니다.\n\n"
    
    if base_description:
        # 기존 설명에서 관련 부분만 추출
        sentences = base_description.split('.')
        relevant_sentences = [s.strip() for s in sentences if any(keyword in s for keyword in ['기본', '과실', '비율', '원칙']) and s.strip()]
        if relevant_sentences:
            enhanced += '. '.join(relevant_sentences[:2]) + '.'
    else:
        enhanced += "신호 준수 여부, 도로 우선권, 안전 확인 의무 등의 기본 원칙에 따라 과실비율이 결정됩니다."
    
    return enhanced


def extract_modification_factors_from_result(result):
    """기존 결과에서 수정 요소 추출"""
    factors = result.get('factors', [])
    if factors:
        return ', '.join(factors)
    
    # 일반적인 가감 요소들
    return "속도위반, 음주운전, 안전확인 의무 위반, 신호위반, 보행자 보호의무 위반"


def extract_modification_description_from_result(result):
    """기존 결과에서 수정 요소 설명 추출"""
    # factors나 final_answer에서 가감요소 설명 찾기
    description = ""
    
    final_answer = result.get('final_answer', '')
    if '가산' in final_answer or '감산' in final_answer or '+' in final_answer or '-' in final_answer:
        # 가감 관련 문장 추출
        sentences = final_answer.split('.')
        relevant_sentences = [s.strip() for s in sentences if any(keyword in s for keyword in ['가산', '감산', '+', '-', '증가', '감소']) and s.strip()]
        if relevant_sentences:
            description = '. '.join(relevant_sentences[:2]) + '.'
    
    if not description:
        description = "일반적인 수정 요소들: 속도위반(+10~20%), 음주운전(+20~30%), 안전확인 의무 위반(+10%), 야간운전(+5%), 어린이보호구역(-10~15%) 등이 최종 과실비율에 반영됩니다."
    
    return description


def extract_final_fault_from_result(result):
    """기존 결과에서 최종 과실 추출"""
    final_answer = result.get('final_answer', '')
    
    # "최종", "결론" 등의 키워드 근처에서 비율 찾기
    import re
    
    final_keywords = ['최종', '결론', '따라서', '결과적으로']
    for keyword in final_keywords:
        if keyword in final_answer:
            # 키워드 이후 부분에서 비율 찾기
            keyword_pos = final_answer.find(keyword)
            after_keyword = final_answer[keyword_pos:keyword_pos+200]  # 200자 정도만
            
            ratio_patterns = [r'(\d+:\d+)', r'(\d+%\s*:\s*\d+%)', r'(\d+\s*대\s*\d+)']
            for pattern in ratio_patterns:
                match = re.search(pattern, after_keyword)
                if match:
                    return match.group(1)
    
    return "구체적 상황 분석 필요"


def extract_legal_info_from_result(result):
    """기존 결과에서 법규 정보 추출"""
    final_answer = result.get('final_answer', '')
    
    # 법규 관련 내용 추출
    legal_keywords = ['도로교통법', '민법', '자동차손해배상', '판례', '법원', '대법원']
    legal_sentences = []
    
    sentences = final_answer.split('.')
    for sentence in sentences:
        if any(keyword in sentence for keyword in legal_keywords):
            legal_sentences.append(sentence.strip())
    
    if legal_sentences:
        return '. '.join(legal_sentences[:3]) + '.'
    
    return "도로교통법 제10조(안전운전 의무), 민법 제750조(불법행위로 인한 손해배상), 자동차손해배상보장법 등이 적용됩니다."


def extract_precedents_from_result(result):
    """기존 결과에서 판례 정보 추출"""
    final_answer = result.get('final_answer', '')
    
    # 판례 관련 내용 추출
    precedent_keywords = ['판례', '대법원', '판결', '법원', '사례']
    precedent_sentences = []
    
    sentences = final_answer.split('.')
    for sentence in sentences:
        if any(keyword in sentence for keyword in precedent_keywords):
            precedent_sentences.append(sentence.strip())
    
    if precedent_sentences:
        return '. '.join(precedent_sentences[:3]) + '.'
    
    return "구체적인 사고 경위, 과속 여부, 신호 위반 여부, 안전 확인 의무 이행 여부 등에 따라 법원의 과실 인정 비율이 달라질 수 있습니다. 비슷한 사고라도 개별 사정에 따른 차이가 있으므로 전문가 상담을 권장합니다."


def create_fallback_result(query, path, selected_option):
    """오류 발생 시 사용할 기본 결과 생성"""
    accident_type = ' > '.join(path) if path else "교통사고"
    
    return {
        "needs_more_input": False,
        "accident_description": f"선택하신 사고 유형: {query}",
        "base_fault": "전문가 상담 필요",
        "base_fault_description": f"{accident_type} 상황에서의 기본 과실비율은 사고의 구체적 경위에 따라 결정되므로 정확한 분석을 위해서는 전문가 상담이 필요합니다.",
        "modification_factors": "다양한 상황별 요소들",
        "modification_description": "속도위반, 신호위반, 안전확인 의무 위반, 음주운전, 졸음운전 등 다양한 요소들이 과실비율 산정에 영향을 줍니다.",
        "final_fault": "개별 사정에 따라 결정",
        "legal_info": "도로교통법, 민법 제750조, 자동차손해배상보장법 등의 관련 법령이 적용됩니다.",
        "precedents": "동일한 유형의 사고라도 구체적 상황에 따라 과실비율이 달라지므로, 판례 검토 및 전문가 상담을 통한 정확한 분석이 필요합니다.",
        "citations": [],
        "error_note": "시스템 처리 중 오류가 발생하여 일반적인 안내를 제공합니다. 정확한 과실비율 산정을 위해서는 전문가와 상담하시기 바랍니다."
    }