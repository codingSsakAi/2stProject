import requests
import json
import os
from datetime import datetime

class CODEFClient:
    def __init__(self):
        self.base_url = "https://api.codef.io/v1/kr/insurance/0003/damoa/insurance-fee"
        self.dev_url = "https://development.codef.io/v1/kr/insurance/0003/damoa/insurance-fee"
        
        # 환경변수에서 CODEF 인증 정보 가져오기
        self.client_id = os.getenv('CODEF_CLIENT_ID')
        self.client_secret = os.getenv('CODEF_CLIENT_SECRET')
        
        # 개발/운영 환경 구분
        self.is_production = os.getenv('CODEF_ENV', 'dev') == 'prod'
        self.api_url = self.base_url if self.is_production else self.dev_url
        
    def get_access_token(self):
        """CODEF API 액세스 토큰 획득"""
        token_url = "https://oauth.codef.io/oauth/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'read'
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            print(f"토큰 획득 오류: {e}")
            return None
    
    def calculate_insurance_fee(self, user_data):
        """보험료 계산"""
        access_token = self.get_access_token()
        if not access_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # 사용자 데이터를 CODEF API 형식으로 변환
        payload = self.prepare_request_data(user_data)
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"보험료 계산 오류: {e}")
            return None
    
    def prepare_request_data(self, user_data):
        """사용자 데이터를 CODEF API 요청 형식으로 변환"""
        
        # 생년월일 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
        birth_date = user_data.get('birth_date', '').replace('-', '') if user_data.get('birth_date') else ''
        
        # 성별 코드 변환
        gender_map = {'M': '1', 'F': '2', 'O': '1'}  # 기타는 남성으로 기본 설정
        identity_enc_yn = gender_map.get(user_data.get('gender', 'M'), '1')
        
        # 현재 날짜를 시작일자로 설정
        start_date = datetime.now().strftime('%Y%m%d')
        
        payload = {
            "organization": "0003",  # 기관코드 (고정)
            "loginType": "6",       # 간편인증 (기본값)
            "identity": "",         # SMS 인증용 (실제 구현시 필요)
            "birthDate": birth_date,
            "identityEncYn": identity_enc_yn,
            "userName": user_data.get('name', ''),
            "phoneNo": user_data.get('phone', ''),
            "telecom": "SKT",       # 통신사 (기본값)
            "timeOut": "60",        # 타임아웃 (기본값)
            "startDate": start_date,
            "brandCode": "0101",    # 메리츠화재 (기본값)
            "carName": "소나타",     # 차종 (기본값)
            "regYear": "2020",      # 등록연도 (기본값)
            "baseCarType": "0",     # 개인용 (기본값)
            "basicAgreement1": "0", # 기본약관1 (기본값)
            "basicAgreement2": "1", # 기본약관2 (기본값)
            "basicAgreement3": "0", # 기본약관3 (기본값)
            "basicAgreement4": "0", # 기본약관4 (기본값)
            "basicAgreement5": "0", # 기본약관5 (기본값)
            "basicAgreement6": "0", # 기본약관6 (기본값)
            "basicAgreement7": "1", # 기본약관7 (기본값)
            "specialDc1": "0",      # 특별할인1 (기본값)
            "blackBoxDc": "1" if user_data.get('has_license') else "0",  # 블랙박스 할인
            "driverRange": "1",     # 운전자 범위 (기본값)
            "type": "1",           # 조회조건 (기본값)
            "useType": "0"         # 용도구분 (기본값)
        }
        
        return payload
    
    def get_insurance_companies(self):
        """지원하는 보험사 목록 반환"""
        companies = {
            "0101": "메리츠화재",
            "0102": "한화손해보험",
            "0103": "롯데손해보험", 
            "0104": "MG손해보험",
            "0105": "흥국화재",
            "0108": "삼성화재",
            "0109": "현대해상",
            "0110": "KB손해보험",
            "0111": "DB손해보험",
            "0112": "AXA다이렉트",
            "0152": "하나손해보험",
            "0195": "캐롯손해보험"
        }
        return companies
    
    def format_insurance_result(self, api_result, user_data):
        """API 결과를 사용자 친화적 형식으로 변환"""
        if not api_result or not api_result.get('result'):
            return None
            
        result_data = api_result.get('result', {})
        
        formatted_result = {
            'user_info': {
                'name': user_data.get('name', ''),
                'birth_date': user_data.get('birth_date', ''),
                'gender': user_data.get('gender', ''),
                'has_license': user_data.get('has_license', False)
            },
            'insurance_info': {
                'company': result_data.get('resCompanyNm', ''),
                'total_premium': result_data.get('resTotalPremium', ''),
                'car_type': result_data.get('resType', ''),
                'special_discounts': result_data.get('resSpecialDcList', [])
            },
            'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'raw_data': api_result  # 디버깅용 원본 데이터
        }
        
        return formatted_result