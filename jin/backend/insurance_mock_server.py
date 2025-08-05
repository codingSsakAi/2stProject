# insurance_mock_server.py
# 완벽한 자동차보험 Mock 서버 구현

import random
import math
from datetime import datetime, timedelta
from django.conf import settings
from typing import Dict, List, Any

class InsuranceMockServer:
    """
    실제 자동차보험 계산 로직을 시뮬레이션하는 Mock 서버
    실제 보험사들의 요율 계산 방식을 참고하여 구현
    """
    
    def __init__(self):
        # 11개 보험사 기본 정보
        self.insurance_companies = {
            '삼성화재': {
                'base_rate': 850000,
                'age_multiplier': {'young': 1.3, 'middle': 1.0, 'senior': 0.85},
                'gender_multiplier': {'M': 1.0, 'F': 0.92},
                'region_multiplier': {'서울': 1.1, '부산': 0.95, '대구': 0.9, '기타': 0.88},
                'experience_bonus': 0.05,  # 1년당 5% 할인
                'accident_penalty': 0.25,  # 사고당 25% 할증
                'car_type_multiplier': {'경차': 0.8, '소형': 0.9, '준중형': 1.0, '중형': 1.15, '대형': 1.3, 'SUV': 1.2},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '무사고 할인 최대 30%'
            },
            '현대해상': {
                'base_rate': 820000,
                'age_multiplier': {'young': 1.25, 'middle': 1.0, 'senior': 0.88},
                'gender_multiplier': {'M': 1.0, 'F': 0.93},
                'region_multiplier': {'서울': 1.08, '부산': 0.96, '대구': 0.91, '기타': 0.89},
                'experience_bonus': 0.04,
                'accident_penalty': 0.22,
                'car_type_multiplier': {'경차': 0.82, '소형': 0.91, '준중형': 1.0, '중형': 1.12, '대형': 1.28, 'SUV': 1.18},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '하이카 앱 할인 15%'
            },
            'KB손해보험': {
                'base_rate': 780000,
                'age_multiplier': {'young': 1.28, 'middle': 1.0, 'senior': 0.87},
                'gender_multiplier': {'M': 1.0, 'F': 0.91},
                'region_multiplier': {'서울': 1.09, '부산': 0.94, '대구': 0.89, '기타': 0.87},
                'experience_bonus': 0.045,
                'accident_penalty': 0.24,
                'car_type_multiplier': {'경차': 0.79, '소형': 0.89, '준중형': 1.0, '중형': 1.14, '대형': 1.32, 'SUV': 1.19},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': 'KB Pay 결제 할인 10%'
            },
            '메리츠화재': {
                'base_rate': 800000,
                'age_multiplier': {'young': 1.32, 'middle': 1.0, 'senior': 0.86},
                'gender_multiplier': {'M': 1.0, 'F': 0.94},
                'region_multiplier': {'서울': 1.12, '부산': 0.97, '대구': 0.92, '기타': 0.90},
                'experience_bonus': 0.042,
                'accident_penalty': 0.26,
                'car_type_multiplier': {'경차': 0.81, '소형': 0.90, '준중형': 1.0, '중형': 1.13, '대형': 1.29, 'SUV': 1.21},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '가족 할인 20%'
            },
            'DB손해보험': {
                'base_rate': 760000,
                'age_multiplier': {'young': 1.35, 'middle': 1.0, 'senior': 0.84},
                'gender_multiplier': {'M': 1.0, 'F': 0.90},
                'region_multiplier': {'서울': 1.13, '부산': 0.93, '대구': 0.88, '기타': 0.86},
                'experience_bonus': 0.048,
                'accident_penalty': 0.27,
                'car_type_multiplier': {'경차': 0.78, '소형': 0.88, '준중형': 1.0, '중형': 1.16, '대형': 1.34, 'SUV': 1.22},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '장기계약 할인 25%'
            },
            '롯데손해보험': {
                'base_rate': 790000,
                'age_multiplier': {'young': 1.29, 'middle': 1.0, 'senior': 0.89},
                'gender_multiplier': {'M': 1.0, 'F': 0.92},
                'region_multiplier': {'서울': 1.10, '부산': 0.95, '대구': 0.90, '기타': 0.88},
                'experience_bonus': 0.043,
                'accident_penalty': 0.23,
                'car_type_multiplier': {'경차': 0.80, '소형': 0.89, '준중형': 1.0, '중형': 1.12, '대형': 1.30, 'SUV': 1.20},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '롯데카드 할인 12%'
            },
            '하나손해보험': {
                'base_rate': 830000,
                'age_multiplier': {'young': 1.26, 'middle': 1.0, 'senior': 0.88},
                'gender_multiplier': {'M': 1.0, 'F': 0.93},
                'region_multiplier': {'서울': 1.07, '부산': 0.96, '대구': 0.91, '기타': 0.89},
                'experience_bonus': 0.041,
                'accident_penalty': 0.21,
                'car_type_multiplier': {'경차': 0.82, '소형': 0.91, '준중형': 1.0, '중형': 1.11, '대형': 1.27, 'SUV': 1.17},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '하나은행 고객 할인 18%'
            },
            '흥국화재': {
                'base_rate': 770000,
                'age_multiplier': {'young': 1.31, 'middle': 1.0, 'senior': 0.85},
                'gender_multiplier': {'M': 1.0, 'F': 0.91},
                'region_multiplier': {'서울': 1.11, '부산': 0.94, '대구': 0.89, '기타': 0.87},
                'experience_bonus': 0.046,
                'accident_penalty': 0.25,
                'car_type_multiplier': {'경차': 0.79, '소형': 0.88, '준중형': 1.0, '중형': 1.15, '대형': 1.33, 'SUV': 1.21},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '인터넷 가입 할인 20%'
            },
            'AXA손해보험': {
                'base_rate': 810000,
                'age_multiplier': {'young': 1.27, 'middle': 1.0, 'senior': 0.87},
                'gender_multiplier': {'M': 1.0, 'F': 0.94},
                'region_multiplier': {'서울': 1.08, '부산': 0.95, '대구': 0.90, '기타': 0.88},
                'experience_bonus': 0.044,
                'accident_penalty': 0.24,
                'car_type_multiplier': {'경차': 0.81, '소형': 0.90, '준중형': 1.0, '중형': 1.13, '대형': 1.31, 'SUV': 1.19},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '외국계 보험사 특별 할인 15%'
            },
            'MG손해보험': {
                'base_rate': 750000,
                'age_multiplier': {'young': 1.33, 'middle': 1.0, 'senior': 0.86},
                'gender_multiplier': {'M': 1.0, 'F': 0.90},
                'region_multiplier': {'서울': 1.14, '부산': 0.93, '대구': 0.88, '기타': 0.86},
                'experience_bonus': 0.049,
                'accident_penalty': 0.28,
                'car_type_multiplier': {'경차': 0.77, '소형': 0.87, '준중형': 1.0, '중형': 1.17, '대형': 1.35, 'SUV': 1.23},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '새마을금고 제휴 할인 22%'
            },
            '캐롯손해보험': {
                'base_rate': 740000,
                'age_multiplier': {'young': 1.20, 'middle': 1.0, 'senior': 0.90},
                'gender_multiplier': {'M': 1.0, 'F': 0.89},
                'region_multiplier': {'서울': 1.05, '부산': 0.92, '대구': 0.87, '기타': 0.85},
                'experience_bonus': 0.052,
                'accident_penalty': 0.20,
                'car_type_multiplier': {'경차': 0.76, '소형': 0.86, '준중형': 1.0, '중형': 1.18, '대형': 1.36, 'SUV': 1.24},
                'coverage_options': ['기본', '표준', '고급', '프리미엄'],
                'special_discount': '텔레매틱스 할인 30%'
            }
        }
        
        # 보장 내용별 가격 배수
        self.coverage_multipliers = {
            '기본': 1.0,
            '표준': 1.2,
            '고급': 1.5,
            '프리미엄': 1.8
        }
        
        # 추가 옵션별 가격
        self.additional_options = {
            '운전자보험': 150000,
            '블랙박스할인': -50000,
            '안전운전할인': -80000,
            '주행거리할인': -60000,
            '환경친화할인': -40000,
            '다자녀할인': -70000
        }

    def get_age_category(self, birth_date: str) -> str:
        """생년월일로 연령대 분류"""
        try:
            birth = datetime.strptime(birth_date, '%Y-%m-%d')
            age = (datetime.now() - birth).days // 365
            
            if age < 26:
                return 'young'
            elif age <= 50:
                return 'middle'
            else:
                return 'senior'
        except:
            return 'middle'  # 기본값

    def calculate_premium(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 프로필 기반 보험료 계산
        실제 보험료 계산 로직을 시뮬레이션
        """
        
        # 사용자 정보 추출
        birth_date = user_profile.get('birth_date', '1990-01-01')
        gender = user_profile.get('gender', 'M')
        region = user_profile.get('residence_area', '서울')
        driving_experience = user_profile.get('driving_experience', 5)
        accident_history = user_profile.get('accident_history', 0)
        car_type = user_profile.get('car_info', {}).get('type', '준중형')
        annual_mileage = user_profile.get('annual_mileage', 12000)
        coverage_level = user_profile.get('coverage_level', '표준')
        
        age_category = self.get_age_category(birth_date)
        
        # 모든 보험사별 견적 계산
        quotes = []
        
        for company_name, company_info in self.insurance_companies.items():
            # 기본 요율
            base_premium = company_info['base_rate']
            
            # 연령대별 요율
            age_multiplier = company_info['age_multiplier'].get(age_category, 1.0)
            
            # 성별 요율
            gender_multiplier = company_info['gender_multiplier'].get(gender, 1.0)
            
            # 지역별 요율
            region_multiplier = company_info['region_multiplier'].get(region, 0.9)
            
            # 차종별 요율
            car_multiplier = company_info['car_type_multiplier'].get(car_type, 1.0)
            
            # 운전경력 할인 (최대 50% 할인)
            experience_discount = min(driving_experience * company_info['experience_bonus'], 0.5)
            
            # 사고이력 할증
            accident_penalty = accident_history * company_info['accident_penalty']
            
            # 연간 주행거리 할인/할증
            mileage_multiplier = 1.0
            if annual_mileage < 5000:
                mileage_multiplier = 0.85  # 저주행 할인
            elif annual_mileage > 20000:
                mileage_multiplier = 1.15  # 고주행 할증
            
            # 보장범위별 요율
            coverage_multiplier = self.coverage_multipliers.get(coverage_level, 1.2)
            
            # 최종 보험료 계산
            final_premium = (
                base_premium * 
                age_multiplier * 
                gender_multiplier * 
                region_multiplier * 
                car_multiplier * 
                mileage_multiplier * 
                coverage_multiplier * 
                (1 - experience_discount) * 
                (1 + accident_penalty)
            )
            
            # 랜덤 변동 요소 추가 (±5%)
            random_factor = random.uniform(0.95, 1.05)
            final_premium *= random_factor
            
            # 월 납입액 계산 (연납 대비 5% 할증)
            monthly_premium = int(final_premium / 12 * 1.05)
            
            # 보험사별 특별 할인 적용 (랜덤하게 적용)
            special_discount_applied = random.choice([True, False])
            if special_discount_applied:
                final_premium *= 0.9  # 10% 추가 할인
            
            quotes.append({
                'company': company_name,
                'annual_premium': int(final_premium),
                'monthly_premium': monthly_premium,
                'coverage_level': coverage_level,
                'coverage_details': self._get_coverage_details(coverage_level),
                'special_discount': company_info['special_discount'] if special_discount_applied else None,
                'discount_rate': f"{int(experience_discount * 100)}%",
                'penalty_rate': f"{int(accident_penalty * 100)}%" if accident_penalty > 0 else "0%",
                'deductible': self._get_deductible_options(),
                'payment_options': ['월납', '연납', '6개월납'],
                'additional_benefits': self._get_additional_benefits(company_name),
                'customer_satisfaction': round(random.uniform(3.8, 4.9), 1),
                'claim_service_rating': round(random.uniform(3.5, 4.8), 1)
            })
        
        # 가격순으로 정렬
        quotes.sort(key=lambda x: x['annual_premium'])
        
        return {
            'result': {
                'code': 'SUCCESS',
                'message': '보험료 계산 완료',
                'timestamp': datetime.now().isoformat(),
                'calculation_id': f'CALC_{random.randint(100000, 999999)}'
            },
            'user_info': {
                'age_category': age_category,
                'risk_level': self._calculate_risk_level(user_profile),
                'recommended_coverage': self._get_recommended_coverage(user_profile)
            },
            'quotes': quotes,
            'market_analysis': {
                'lowest_premium': quotes[0]['annual_premium'],
                'highest_premium': quotes[-1]['annual_premium'],
                'average_premium': int(sum(q['annual_premium'] for q in quotes) / len(quotes)),
                'price_difference': quotes[-1]['annual_premium'] - quotes[0]['annual_premium'],
                'best_value': self._find_best_value(quotes)
            }
        }

    def _get_coverage_details(self, level: str) -> Dict[str, str]:
        """보장 범위별 상세 내용"""
        details = {
            '기본': {
                '대인배상': '무한',
                '대물배상': '2억원',
                '자동차상해': '1.5억원',
                '자차': '가입금액',
                '자기신체사고': '1천만원'
            },
            '표준': {
                '대인배상': '무한',
                '대물배상': '5억원',
                '자동차상해': '2억원',
                '자차': '가입금액',
                '자기신체사고': '3천만원',
                '무보험차상해': '2억원'
            },
            '고급': {
                '대인배상': '무한',
                '대물배상': '10억원',
                '자동차상해': '3억원',
                '자차': '가입금액',
                '자기신체사고': '5천만원',
                '무보험차상해': '3억원',
                '담보운전자확대': '포함'
            },
            '프리미엄': {
                '대인배상': '무한',
                '대물배상': '20억원',
                '자동차상해': '5억원',
                '자차': '가입금액',
                '자기신체사고': '1억원',
                '무보험차상해': '5억원',
                '담보운전자확대': '포함',
                '개인용품손해': '300만원',
                '대여차량비용': '포함'
            }
        }
        return details.get(level, details['표준'])

    def _get_deductible_options(self) -> Dict[str, int]:
        """자기부담금 옵션"""
        return {
            '자차': random.choice([200000, 300000, 500000]),
            '자기신체사고': random.choice([100000, 200000]),
            '대물': random.choice([0, 200000])
        }

    def _get_additional_benefits(self, company: str) -> List[str]:
        """보험사별 추가 혜택"""
        benefits_pool = [
            '24시간 긴급출동서비스',
            '렌터카 서비스',
            '대리운전 서비스',
            '무료견인 서비스',
            '정비소 할인',
            '주유할인',
            '세차할인',
            '타이어 무상교체',
            '유리창 무상수리',
            '변호사 비용 지원',
            '의료진 직통상담',
            '교통사고 심리상담'
        ]
        return random.sample(benefits_pool, random.randint(4, 8))

    def _calculate_risk_level(self, user_profile: Dict[str, Any]) -> str:
        """사용자 위험도 계산"""
        risk_score = 0
        
        # 나이별 위험도
        age_category = self.get_age_category(user_profile.get('birth_date', '1990-01-01'))
        if age_category == 'young':
            risk_score += 3
        elif age_category == 'senior':
            risk_score += 1
        
        # 운전경력
        experience = user_profile.get('driving_experience', 5)
        if experience < 3:
            risk_score += 2
        elif experience > 10:
            risk_score -= 1
        
        # 사고이력
        accidents = user_profile.get('accident_history', 0)
        risk_score += accidents * 2
        
        # 주행거리
        mileage = user_profile.get('annual_mileage', 12000)
        if mileage > 20000:
            risk_score += 2
        elif mileage < 5000:
            risk_score -= 1
        
        # 위험도 분류
        if risk_score <= 1:
            return '낮음'
        elif risk_score <= 4:
            return '보통'
        else:
            return '높음'

    def _get_recommended_coverage(self, user_profile: Dict[str, Any]) -> str:
        """추천 보장 수준"""
        risk_level = self._calculate_risk_level(user_profile)
        age_category = self.get_age_category(user_profile.get('birth_date', '1990-01-01'))
        
        if risk_level == '높음' or age_category == 'young':
            return '프리미엄'
        elif risk_level == '보통':
            return '고급'
        else:
            return '표준'

    def _find_best_value(self, quotes: List[Dict]) -> str:
        """가성비 최고 상품 찾기"""
        best_company = None
        best_score = 0
        
        for quote in quotes:
            # 가격 점수 (낮을수록 좋음, 역수 적용)
            price_score = 1000000 / quote['annual_premium']
            
            # 고객만족도 점수
            satisfaction_score = quote['customer_satisfaction'] * 100
            
            # 클레임 서비스 점수
            claim_score = quote['claim_service_rating'] * 100
            
            # 종합 점수
            total_score = price_score + satisfaction_score + claim_score
            
            if total_score > best_score:
                best_score = total_score
                best_company = quote['company']
        
        return best_company

    def get_company_detail(self, company_name: str) -> Dict[str, Any]:
        """특정 보험사 상세 정보"""
        if company_name not in self.insurance_companies:
            return {"error": "보험사를 찾을 수 없습니다."}
        
        company = self.insurance_companies[company_name]
        
        return {
            'company_name': company_name,
            'establishment_year': random.randint(1960, 1990),
            'market_share': f"{random.uniform(5.2, 15.8):.1f}%",
            'financial_rating': random.choice(['AA-', 'A+', 'A', 'A-']),
            'claim_settlement_ratio': f"{random.uniform(95.2, 99.8):.1f}%",
            'customer_service_hours': '24시간 연중무휴',
            'branch_count': random.randint(150, 450),
            'special_programs': [
                company['special_discount'],
                '신규가입 할인 20%',
                '장기보험 할인 15%',
                '무사고 할인 누적 최대 50%'
            ],
            'digital_services': [
                '모바일 앱',
                '웹사이트 가입',
                'AI 상담챗봇',
                '온라인 사고접수',
                '실시간 보험료 계산'
            ],
            'partnership_benefits': self._get_partnership_benefits(company_name)
        }

    def _get_partnership_benefits(self, company_name: str) -> List[str]:
        """제휴 혜택"""
        partnerships = {
            '삼성화재': ['삼성카드 할인', 'GS칼텍스 주유할인', '삼성전자 제품할인'],
            '현대해상': ['현대카드 할인', 'S-Oil 주유할인', '현대백화점 할인'],
            'KB손해보험': ['KB카드 할인', '국민은행 할인', 'KB스타뱅킹 연동'],
            '메리츠화재': ['신한카드 할인', '신한은행 할인', 'SK주유소 할인'],
            'DB손해보험': ['우리카드 할인', '우리은행 할인', 'GS25 할인'],
        }
        
        return partnerships.get(company_name, ['제휴카드 할인', '주유소 할인', '마트 할인'])

    def get_market_trends(self) -> Dict[str, Any]:
        """자동차보험 시장 동향"""
        return {
            'market_size': '약 20조원 (2024년 기준)',
            'average_premium_change': f"{random.uniform(-2.5, 3.2):+.1f}% (전년 대비)",
            'popular_coverage': '표준형 (전체의 45%)',
            'online_subscription_rate': f"{random.uniform(65, 82):.1f}%",
            'claim_frequency': f"계약 100건당 {random.uniform(8.5, 12.3):.1f}건",
            'trends': [
                '텔레매틱스 보험 확산',
                'AI 기반 언더라이팅 도입',
                '모바일 중심 서비스 확대',
                '개인화된 보험료 산정',
                '친환경차 할인 확대'
            ],
            'regulatory_changes': [
                '자율주행차 보험 가이드라인 마련',
                '개인정보보호 강화',
                '소비자 권익 강화',
                '보험료 산정 투명성 제고'
            ]
        }

# Django 서비스 클래스에 통합하는 예시
class InsuranceService:
    def __init__(self):
        self.mock_server = InsuranceMockServer()
        self.use_mock = getattr(settings, 'USE_MOCK_API', True)
    
    def calculate_insurance_premium(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """보험료 계산 메인 함수"""
        if self.use_mock:
            return self.mock_server.calculate_premium(user_profile)
        else:
            # 실제 CODEF API 호출 로직
            return self._call_real_codef_api(user_profile)
    
    def get_company_information(self, company_name: str) -> Dict[str, Any]:
        """보험사 정보 조회"""
        if self.use_mock:
            return self.mock_server.get_company_detail(company_name)
        else:
            # 실제 API 호출
            return self._get_real_company_info(company_name)
    
    def get_market_analysis(self) -> Dict[str, Any]:
        """시장 분석 정보"""
        if self.use_mock:
            return self.mock_server.get_market_trends()
        else:
            # 실제 시장 데이터 API 호출
            return self._get_real_market_data()
    
    def _call_real_codef_api(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """실제 CODEF API 호출 (추후 구현)"""
        # from easycodefpy import Codef, ServiceType
        # codef = Codef()
        # ... 실제 API 호출 로직
        pass
    
    def _get_real_company_info(self, company_name: str) -> Dict[str, Any]:
        """실제 보험사 정보 API 호출 (추후 구현)"""
        pass
    
    def _get_real_market_data(self) -> Dict[str, Any]:
        """실제 시장 데이터 API 호출 (추후 구현)"""
        pass

# 사용 예시
if __name__ == "__main__":
    # Mock 서버 테스트
    mock_server = InsuranceMockServer()
    
    # 테스트 사용자 프로필
    test_profile = {
        'birth_date': '1990-05-15',
        'gender': 'M',
        'residence_area': '서울',
        'driving_experience': 8,
        'accident_history': 1,
        'annual_mileage': 15000,
        'car_info': {'type': '준중형'},
        'coverage_level': '표준'
    }
    
    # 보험료 계산 테스트
    result = mock_server.calculate_premium(test_profile)
    
    print("=== 보험료 계산 결과 ===")
    print(f"계산 ID: {result['result']['calculation_id']}")
    print(f"사용자 위험도: {result['user_info']['risk_level']}")
    print(f"추천 보장: {result['user_info']['recommended_coverage']}")
    print(f"평균 보험료: {result['market_analysis']['average_premium']:,}원")
    print(f"가성비 최고: {result['market_analysis']['best_value']}")
    
    print("\n=== 상위 3개 보험사 견적 ===")
    for i, quote in enumerate(result['quotes'][:3], 1):
        print(f"{i}. {quote['company']}")
        print(f"   연간 보험료: {quote['annual_premium']:,}원")
        print(f"   월 납입액: {quote['monthly_premium']:,}원")
        print(f"   고객만족도: {quote['customer_satisfaction']}/5.0")
        if quote['special_discount']:
            print(f"   특별할인: {quote['special_discount']}")
        print()

# Mock 서버를 Django Views에서 사용하는 예시
"""
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def calculate_insurance_premium(request):
    if request.method == 'POST':
        try:
            user_data = json.loads(request.body)
            
            # Mock 서버로 보험료 계산
            insurance_service = InsuranceService()
            result = insurance_service.calculate_insurance_premium(user_data)
            
            return JsonResponse(result)
        
        except Exception as e:
            return JsonResponse({
                'result': {
                    'code': 'ERROR',
                    'message': f'계산 중 오류 발생: {str(e)}'
                }
            }, status=500)
    
    return JsonResponse({'error': 'POST method required'}, status=405)

@csrf_exempt
def get_company_detail(request, company_name):
    insurance_service = InsuranceService()
    result = insurance_service.get_company_information(company_name)
    return JsonResponse(result)
"""
                