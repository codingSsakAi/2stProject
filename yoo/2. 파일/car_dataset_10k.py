# 자동차보험 고객 데이터 생성 (간소화 버전)
# 통계청 기반 현실적 데이터 1만명 생성

import pandas as pd
import numpy as np
from datetime import datetime
import random
import warnings
warnings.filterwarnings('ignore')

# 시드 고정
np.random.seed(42)
random.seed(42)

print("=== 자동차보험 고객 데이터 생성 ===")
print("샘플 규모: 10,000명")

# 통계청 기반 실제 데이터
KOREA_STATISTICS = {
    'age_distribution': {
        '20-24': 0.06, '25-29': 0.12, '30-34': 0.15, '35-39': 0.16, '40-44': 0.15,
        '45-49': 0.14, '50-54': 0.12, '55-59': 0.08, '60-64': 0.06, '65-69': 0.06
    },
    
    'region_distribution': {
        '서울': 0.188, '경기': 0.252, '부산': 0.069, '대구': 0.049, '인천': 0.058,
        '광주': 0.030, '대전': 0.030, '울산': 0.023, '강원': 0.031, '충북': 0.032,
        '충남': 0.043, '전북': 0.037, '전남': 0.038, '경북': 0.055, '경남': 0.069, '제주': 0.013
    },
    
    'income_distribution': {
        '1분위(하위20%)': {'range': (0, 150), 'ratio': 0.20},
        '2분위': {'range': (150, 250), 'ratio': 0.20},
        '3분위(중위)': {'range': (250, 350), 'ratio': 0.20},
        '4분위': {'range': (350, 500), 'ratio': 0.20},
        '5분위(상위20%)': {'range': (500, 1000), 'ratio': 0.20}
    },
    
    'car_ownership_rate': 0.821,
    'gender_ratio': {'M': 0.512, 'F': 0.488},
    
    'occupation_distribution': {
        '사무직': 0.28, '서비스업': 0.18, '전문직': 0.15, '공무원': 0.08,
        '제조업': 0.12, '영업직': 0.08, '자영업': 0.06, '운수업': 0.03, '건설업': 0.02
    }
}

# 보험 상품 정의
INSURANCE_PRODUCTS = {
    'basic': '기본형',
    'standard': '표준형', 
    'premium': '고급형',
    'super_premium': '프리미엄'
}

class InsuranceDataGenerator:
    """자동차보험 고객 데이터 생성기"""
    
    def __init__(self):
        self.korea_stats = KOREA_STATISTICS
        
    def generate_sample(self, n_samples=10000):
        """현실적인 고객 샘플 생성"""
        print(f"{n_samples:,}명 샘플 데이터 생성 중...")
        
        samples = []
        
        for i in range(n_samples):
            sample = {}
            
            # 1. 기본 인구통계
            sample.update(self._generate_demographics())
            
            # 2. 경제 정보
            sample.update(self._generate_economic_info(sample))
            
            # 3. 운전/차량 정보
            sample.update(self._generate_driving_info(sample))
            
            # 4. 보험 가입 현황
            sample.update(self._generate_insurance_status(sample))
            
            # 5. 고유 ID
            sample['customer_id'] = f'C{i+1:06d}'
            sample['data_created_date'] = datetime.now().strftime('%Y-%m-%d')
            
            samples.append(sample)
            
            if (i + 1) % 2000 == 0:
                print(f"진행률: {i+1:,}/{n_samples:,} ({(i+1)/n_samples*100:.1f}%)")
        
        return pd.DataFrame(samples)
    
    def _generate_demographics(self):
        """인구통계학적 정보 생성"""
        
        # 1. 연령 생성
        age_groups = list(self.korea_stats['age_distribution'].keys())
        age_probs = list(self.korea_stats['age_distribution'].values())
        age_probs = np.array(age_probs)
        age_probs = age_probs / age_probs.sum()
        selected_age_group = np.random.choice(age_groups, p=age_probs)
        
        age_ranges = {
            '20-24': (20, 24), '25-29': (25, 29), '30-34': (30, 34),
            '35-39': (35, 39), '40-44': (40, 44), '45-49': (45, 49),
            '50-54': (50, 54), '55-59': (55, 59), '60-64': (60, 64),
            '65-69': (65, 69)
        }
        
        min_age, max_age = age_ranges[selected_age_group]
        age = np.random.randint(min_age, max_age + 1)
        
        # 2. 성별
        gender = np.random.choice(['M', 'F'], 
                                p=[self.korea_stats['gender_ratio']['M'], 
                                   self.korea_stats['gender_ratio']['F']])
        
        # 3. 거주지역
        regions = list(self.korea_stats['region_distribution'].keys())
        region_probs = list(self.korea_stats['region_distribution'].values())
        region_probs = np.array(region_probs)
        region_probs = region_probs / region_probs.sum()
        residence_area = np.random.choice(regions, p=region_probs)
        
        # 4. 생년월일
        birth_year = 2024 - age
        birth_date = f"{birth_year}-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}"
        
        return {
            'age': age,
            'age_group': selected_age_group,
            'gender': gender,
            'residence_area': residence_area,
            'birth_date': birth_date
        }
    
    def _generate_economic_info(self, sample):
        """경제 정보 생성"""
        
        # 1. 직업
        occupations = list(self.korea_stats['occupation_distribution'].keys())
        occ_probs = list(self.korea_stats['occupation_distribution'].values())
        occ_probs = np.array(occ_probs)
        occ_probs = occ_probs / occ_probs.sum()
        occupation = np.random.choice(occupations, p=occ_probs)
        
        # 2. 소득 (연령, 직업에 따라 조정)
        age = sample['age']
        
        # 연령별 소득 가중치
        if age < 30:
            income_weights = [0.35, 0.30, 0.20, 0.12, 0.03]
        elif age < 45:
            income_weights = [0.15, 0.20, 0.25, 0.25, 0.15]
        elif age < 60:
            income_weights = [0.10, 0.15, 0.25, 0.30, 0.20]
        else:
            income_weights = [0.20, 0.25, 0.30, 0.20, 0.05]
        
        # 직업별 소득 조정
        job_income_multipliers = {
            '전문직': [0.05, 0.10, 0.20, 0.35, 0.30],
            '공무원': [0.10, 0.20, 0.35, 0.25, 0.10],
            '사무직': [0.15, 0.25, 0.30, 0.20, 0.10],
            '영업직': [0.20, 0.25, 0.25, 0.20, 0.10],
            '서비스업': [0.35, 0.30, 0.20, 0.12, 0.03],
            '제조업': [0.25, 0.30, 0.25, 0.15, 0.05],
            '자영업': [0.30, 0.20, 0.20, 0.15, 0.15],
            '운수업': [0.30, 0.35, 0.25, 0.08, 0.02],
            '건설업': [0.25, 0.35, 0.25, 0.12, 0.03]
        }
        
        if occupation in job_income_multipliers:
            income_weights = job_income_multipliers[occupation]
        
        # 소득 구간 선택
        income_groups = list(self.korea_stats['income_distribution'].keys())
        income_weights = np.array(income_weights)
        income_weights = income_weights / income_weights.sum()
        selected_income_group = np.random.choice(income_groups, p=income_weights)
        income_range = self.korea_stats['income_distribution'][selected_income_group]['range']
        
        monthly_income = np.random.randint(income_range[0], income_range[1] + 1)
        annual_income = monthly_income * 12 * 10000
        
        # 소득 분류
        if monthly_income < 200:
            income_level = '저소득'
        elif monthly_income < 300:
            income_level = '중저소득'
        elif monthly_income < 450:
            income_level = '중간소득'
        elif monthly_income < 700:
            income_level = '중고소득'
        else:
            income_level = '고소득'
        
        return {
            'occupation': occupation,
            'monthly_income': monthly_income,
            'annual_income': annual_income,
            'income_level': income_level
        }
    
    def _generate_driving_info(self, sample):
        """운전/차량 정보 생성"""
        
        # 차량 보유 여부
        has_car = np.random.random() < self.korea_stats['car_ownership_rate']
        
        if not has_car:
            return {
                'has_car': False,
                'driving_experience': 0,
                'annual_mileage': 0,
                'accident_history': 0,
                'car_type': None,
                'car_brand': None,
                'car_year': None,
                'car_number': None
            }
        
        # 운전경력
        age = sample['age']
        max_experience = age - 18
        if max_experience <= 0:
            driving_experience = 0
        else:
            experience_ratio = np.random.beta(2, 3)
            driving_experience = int(max_experience * experience_ratio)
            driving_experience = max(1, driving_experience)
        
        # 연간 주행거리
        base_mileage = np.random.lognormal(9.3, 0.6)
        
        # 직업별 조정
        job_multipliers = {
            '운수업': 2.5, '영업직': 1.8, '서비스업': 1.3,
            '자영업': 1.4, '건설업': 1.5, '제조업': 1.2,
            '사무직': 1.0, '전문직': 0.9, '공무원': 0.9
        }
        
        occupation = sample['occupation']
        job_mult = job_multipliers.get(occupation, 1.0)
        
        # 지역별 조정
        urban_areas = ['서울', '부산', '대구', '인천', '광주', '대전', '울산']
        if sample['residence_area'] in urban_areas:
            region_mult = 0.85
        else:
            region_mult = 1.25
        
        # 나이별 조정
        if age < 30:
            age_mult = 1.1
        elif age > 60:
            age_mult = 0.7
        else:
            age_mult = 1.0
        
        annual_mileage = base_mileage * job_mult * region_mult * age_mult
        annual_mileage = max(3000, min(80000, int(annual_mileage)))
        
        # 사고이력
        accident_base_prob = 0.05
        if age < 25:
            accident_base_prob += 0.03
        if driving_experience < 3:
            accident_base_prob += 0.02
        if annual_mileage > 25000:
            accident_base_prob += 0.02
        
        accident_history = np.random.poisson(accident_base_prob * 3)
        accident_history = min(5, accident_history)
        
        # 차량 정보
        car_info = self._generate_car_info(sample)
        
        return {
            'has_car': True,
            'driving_experience': driving_experience,
            'annual_mileage': annual_mileage,
            'accident_history': accident_history,
            **car_info
        }
    
    def _generate_car_info(self, sample):
        """차량 정보 생성"""
        
        income_level = sample.get('income_level', '중간소득')
        
        if income_level in ['저소득', '중저소득']:
            car_brands = ['현대', '기아', '쉐보레', '르노삼성']
            brand_probs = [0.45, 0.35, 0.15, 0.05]
            car_types = ['경차', '소형', '준중형']
            type_probs = [0.3, 0.4, 0.3]
        elif income_level == '중간소득':
            car_brands = ['현대', '기아', '제네시스', '쉐보레']
            brand_probs = [0.4, 0.3, 0.15, 0.15]
            car_types = ['소형', '준중형', '중형']
            type_probs = [0.2, 0.5, 0.3]
        elif income_level == '중고소득':
            car_brands = ['현대', '기아', '제네시스', '벤츠', 'BMW']
            brand_probs = [0.3, 0.25, 0.2, 0.15, 0.1]
            car_types = ['준중형', '중형', 'SUV']
            type_probs = [0.3, 0.4, 0.3]
        else:  # 고소득
            car_brands = ['제네시스', '벤츠', 'BMW', '아우디', '렉서스']
            brand_probs = [0.25, 0.25, 0.2, 0.15, 0.15]
            car_types = ['중형', '대형', 'SUV', '수입차']
            type_probs = [0.25, 0.25, 0.3, 0.2]
        
        car_brand = np.random.choice(car_brands, p=brand_probs)
        car_type = np.random.choice(car_types, p=type_probs)
        
        # 차량 연식
        if income_level in ['저소득', '중저소득']:
            car_years = list(range(2010, 2025))
            year_weights = [0.15, 0.12, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01, 0.01]
        else:
            car_years = list(range(2015, 2025))
            year_weights = [0.05, 0.05, 0.08, 0.10, 0.12, 0.15, 0.15, 0.12, 0.10, 0.08]
        
        # 확률 정규화
        year_weights = np.array(year_weights)
        year_weights = year_weights / year_weights.sum()
        
        car_year = np.random.choice(car_years, p=year_weights)
        car_number = f"{np.random.randint(10,100)}가{np.random.randint(1000,10000)}"
        
        return {
            'car_brand': car_brand,
            'car_type': car_type,
            'car_year': car_year,
            'car_number': car_number
        }
    
    def _generate_insurance_status(self, sample):
        """보험 가입 현황 생성"""
        
        if not sample.get('has_car', False):
            return {
                'has_insurance': False,
                'current_insurance_company': None,
                'current_product_type': None,
                'monthly_premium': 0
            }
        
        # 자동차보험 의무가입 (98% 가입률)
        has_insurance = np.random.random() < 0.98
        
        if not has_insurance:
            return {
                'has_insurance': False,
                'current_insurance_company': None,
                'current_product_type': None,
                'monthly_premium': 0
            }
        
        # 보험사 선택 (실제 시장점유율 반영)
        insurance_companies = ['삼성화재해상보험', '현대해상화재보험', 'KB손해보험', '메리츠화재보험', 'DB손해보험', 
                             '롯데손해보험', '한화손해보험', 'MG손해보험','흥국화재해상보험','AXA손해보험','하나손해보험','캐롯손해보험']
        company_shares = [0.102, 0.119, 0.084, 0.101, 0.081, 0.087, 0.069, 0.054, 0.106, 0.052, 0.083, 0.062]
        
        current_company = np.random.choice(insurance_companies, p=company_shares)
        
        # 상품 선택 (연령, 소득 기반)
        age = sample['age']
        income_level = sample['income_level']
        
        # 연령대별 상품 선호도
        if age < 30:
            product_probs = [0.6, 0.3, 0.08, 0.02]  # 기본형 선호
        elif age < 45:
            product_probs = [0.2, 0.5, 0.25, 0.05]  # 표준형 선호
        elif age < 60:
            product_probs = [0.15, 0.4, 0.35, 0.1]  # 고급형 선호
        else:
            product_probs = [0.25, 0.35, 0.3, 0.1]  # 보수적 선택
        
        # 소득별 조정
        if income_level in ['저소득', '중저소득']:
            product_probs = [0.7, 0.25, 0.05, 0.0]
        elif income_level == '고소득':
            product_probs = [0.05, 0.2, 0.45, 0.3]
        
        products = list(INSURANCE_PRODUCTS.keys())
        current_product = np.random.choice(products, p=product_probs)
        
        # 보험료 계산
        base_premiums = {'basic': 65, 'standard': 85, 'premium': 105, 'super_premium': 125}
        base_premium = base_premiums[current_product]
        
        # 개인 위험도 반영
        risk_multiplier = 1.0
        if age < 26:
            risk_multiplier += 0.3
        elif age > 60:
            risk_multiplier -= 0.1
        
        risk_multiplier += sample.get('accident_history', 0) * 0.2
        
        monthly_premium = int(base_premium * risk_multiplier * np.random.uniform(0.8, 1.2))
        
        return {
            'has_insurance': True,
            'current_insurance_company': current_company,
            'current_product_type': INSURANCE_PRODUCTS[current_product],
            'monthly_premium': monthly_premium
        }

# 데이터 생성 실행
print("\n=== 데이터 생성 시작 ===")

generator = InsuranceDataGenerator()
insurance_data = generator.generate_sample(n_samples=10000)

print(f"\n✅ 생성 완료! 데이터 크기: {insurance_data.shape}")

# 기본 통계 출력
print("\n=== 기본 통계 ===")
total_drivers = len(insurance_data[insurance_data['has_car'] == True])
insured_drivers = len(insurance_data[insurance_data['has_insurance'] == True])

print(f"전체 고객: {len(insurance_data):,}명")
print(f"차량 보유자: {total_drivers:,}명 ({total_drivers/len(insurance_data):.1%})")
print(f"보험 가입자: {insured_drivers:,}명 ({insured_drivers/total_drivers:.1%})")

# 상품별 가입 현황
print(f"\n보험 상품별 가입 현황:")
insured_data = insurance_data[insurance_data['has_insurance'] == True]
product_dist = insured_data['current_product_type'].value_counts()
for product, count in product_dist.items():
    print(f"  {product}: {count:,}명 ({count/len(insured_data):.1%})")

# 보험사별 가입 현황
print(f"\n보험사별 가입 현황:")
company_dist = insured_data['current_insurance_company'].value_counts()
for company, count in company_dist.items():
    print(f"  {company}: {count:,}명 ({count/len(insured_data):.1%})")

print(f"\n평균 월 보험료: {insured_data['monthly_premium'].mean():.0f}만원")

# 데이터 저장
print(f"\n=== 데이터 저장 ===")
insurance_data.to_csv('car_insurance_customers_10k.csv', index=False, encoding='utf-8-sig')
print("✅ car_insurance_customers_10k.csv 파일로 저장 완료")

# 샘플 데이터 출력
print(f"\n=== 샘플 데이터 ===")
print(insurance_data.head(3))

print(f"\n=== 생성 완료 ===")
print(f"파일명: car_insurance_customers_10k.csv")
print(f"총 고객 수: {len(insurance_data):,}명")
print(f"컬럼 수: {len(insurance_data.columns)}개")