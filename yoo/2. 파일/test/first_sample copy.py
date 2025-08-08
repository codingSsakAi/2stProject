# 자동차보험 전문 추천 시스템 - ML 모델 및 유사 회원 분석
# 웹/앱 서비스용 자동차보험 맞춤 추천 및 유사 운전자 분석

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import random
import warnings
from typing import Dict, List, Any, Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.neighbors import NearestNeighbors
import warnings
warnings.filterwarnings('ignore')

# 시드 고정
np.random.seed(42)
random.seed(42)

print("=== 자동차보험 전문 추천 시스템 ===")
print("1. 자동차보험 상품별 맞춤 추천")
print("2. 유사 운전자 가입 패턴 분석")

# 자동차보험 상품 정의 (기존 Mock 서버와 연계)
CAR_INSURANCE_PRODUCTS = {
    'basic': {
        'name': '자동차보험 기본형',
        'description': '필수 보장 중심의 경제적 상품',
        'coverage': {
            '대인배상': '무한',
            '대물배상': '2억원',
            '자동차상해': '1.5억원',
            '자차': '가입금액',
            '자기신체사고': '1천만원'
        },
        'target_customer': '경제성 중시, 기본 보장 필요',
        'avg_premium': 650000
    },
    'standard': {
        'name': '자동차보험 표준형',
        'description': '기본 + 추가 보장의 균형잡힌 상품',
        'coverage': {
            '대인배상': '무한',
            '대물배상': '5억원',
            '자동차상해': '2억원',
            '자차': '가입금액',
            '자기신체사고': '3천만원',
            '무보험차상해': '2억원'
        },
        'target_customer': '적정한 보장과 가격의 균형 추구',
        'avg_premium': 780000
    },
    'premium': {
        'name': '자동차보험 고급형',
        'description': '충분한 보장의 안심 상품',
        'coverage': {
            '대인배상': '무한',
            '대물배상': '10억원',
            '자동차상해': '3억원',
            '자차': '가입금액',
            '자기신체사고': '5천만원',
            '무보험차상해': '3억원',
            '담보운전자확대': '포함'
        },
        'target_customer': '충분한 보장 선호, 중간 이상 소득',
        'avg_premium': 950000
    },
    'super_premium': {
        'name': '자동차보험 프리미엄',
        'description': '최고 수준 보장의 프리미엄 상품',
        'coverage': {
            '대인배상': '무한',
            '대물배상': '20억원',
            '자동차상해': '5억원',
            '자차': '가입금액',
            '자기신체사고': '1억원',
            '무보험차상해': '5억원',
            '담보운전자확대': '포함',
            '개인용품손해': '300만원',
            '대여차량비용': '포함'
        },
        'target_customer': '최고 보장 선호, 고소득층',
        'avg_premium': 1200000
    }
}

# 보험사 정보 (기존 Mock 서버와 동일)
INSURANCE_COMPANIES = [
    '삼성화재', '현대해상', 'KB손해보험', '메리츠화재', 'DB손해보험',
    '롯데손해보험', '하나손해보험', '흥국화재', 'AXA손해보험', 'MG손해보험', '캐롯손해보험'
]

class CarInsuranceRecommendationSystem:
    """자동차보험 전문 추천 시스템"""
    
    def __init__(self):
        self.products = CAR_INSURANCE_PRODUCTS
        self.companies = INSURANCE_COMPANIES
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.recommendation_model = None
        self.similarity_model = None
        self.user_profiles = None
        
    def generate_driver_data(self, n_drivers=12000):
        """실제 자동차보험 가입 고객 데이터 시뮬레이션"""
        print("자동차보험 고객 데이터 생성 중...")
        
        drivers = []
        
        for i in range(n_drivers):
            # 1. 기본 정보
            age = np.random.choice(range(20, 70), p=self._get_driver_age_distribution())
            birth_year = 2024 - age
            birth_date = f"{birth_year}-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}"
            
            gender = np.random.choice(['M', 'F'], p=[0.58, 0.42])  # 남성 운전자 비율 높음
            
            # 2. 거주지역
            regions = ['서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
            region_probs = [0.19, 0.26, 0.07, 0.05, 0.06, 0.03, 0.03, 0.02, 0.03, 0.03, 0.04, 0.04, 0.04, 0.05, 0.05, 0.01]
            residence_area = np.random.choice(regions, p=region_probs)
            
            # 3. 직업 (자동차보험과 연관성 고려)
            occupations = {
                '사무직': {'risk': 'low', 'income_range': (3000, 6000), 'prob': 0.28},
                '전문직': {'risk': 'low', 'income_range': (5000, 12000), 'prob': 0.15},
                '공무원': {'risk': 'low', 'income_range': (3500, 7000), 'prob': 0.12},
                '운수업': {'risk': 'high', 'income_range': (2800, 4500), 'prob': 0.08},
                '영업직': {'risk': 'medium', 'income_range': (3000, 7000), 'prob': 0.12},
                '서비스업': {'risk': 'medium', 'income_range': (2500, 4500), 'prob': 0.10},
                '제조업': {'risk': 'medium', 'income_range': (2800, 5500), 'prob': 0.08},
                '건설업': {'risk': 'high', 'income_range': (3000, 6000), 'prob': 0.04},
                '자영업': {'risk': 'medium', 'income_range': (2000, 10000), 'prob': 0.03}
            }
            
            occupation = np.random.choice(list(occupations.keys()), 
                                        p=[info['prob'] for info in occupations.values()])
            job_risk_level = occupations[occupation]['risk']
            
            # 연소득
            income_range = occupations[occupation]['income_range']
            annual_income = np.random.randint(income_range[0], income_range[1] + 1) * 10000
            
            # 4. 운전 관련 정보
            driving_experience = min(age - 18, max(1, int(np.random.exponential(age/4))))
            
            # 연간 주행거리 (직업과 상관관계)
            base_mileage = np.random.lognormal(9.4, 0.6)  # 평균 약 12,000km
            
            if job_risk_level == 'high':
                mileage_multiplier = 1.6  # 운수업, 건설업 등
            elif occupation == '영업직':
                mileage_multiplier = 1.4
            elif residence_area in ['서울', '부산', '대구', '인천']:
                mileage_multiplier = 0.8  # 대도시
            else:
                mileage_multiplier = 1.2
                
            annual_mileage = int(base_mileage * mileage_multiplier)
            annual_mileage = max(3000, min(60000, annual_mileage))
            
            # 5. 사고 이력 (나이, 경력, 주행거리 고려)
            accident_prob = (
                0.08 +  # 기본 확률
                max(0, (25 - age) * 0.005) +  # 젊은 운전자 위험
                (annual_mileage / 100000) * 0.15 +  # 주행거리
                max(0, (3 - driving_experience) * 0.02) +  # 초보 운전자
                {'high': 0.05, 'medium': 0.02, 'low': 0}[job_risk_level]  # 직업 위험도
            )
            
            accident_history = np.random.poisson(accident_prob * 3)  # 최근 3년
            accident_history = min(5, accident_history)
            
            # 6. 차량 정보
            car_brands = ['현대', '기아', '제네시스', '벤츠', 'BMW', '아우디', '토요타', '볼보', '기타']
            brand_probs = [0.38, 0.28, 0.08, 0.08, 0.06, 0.03, 0.04, 0.02, 0.03]
            car_brand = np.random.choice(car_brands, p=brand_probs)
            
            # 차량 종류 (소득과 상관관계)
            if annual_income > 80000000:
                car_types = ['중형', '대형', 'SUV', '수입차']
                car_type_probs = [0.3, 0.2, 0.3, 0.2]
            elif annual_income > 50000000:
                car_types = ['준중형', '중형', 'SUV']
                car_type_probs = [0.4, 0.4, 0.2]
            else:
                car_types = ['경차', '소형', '준중형']
                car_type_probs = [0.2, 0.4, 0.4]
            
            car_type = np.random.choice(car_types, p=car_type_probs)
            
            # 차량 연식
            car_year = np.random.choice(range(2015, 2025), 
                                      p=[0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.17, 0.15, 0.10, 0.05])
            car_age = 2024 - car_year
            
            # 배기량 (차종에 따라)
            engine_size_map = {
                '경차': [800, 1000],
                '소형': [1000, 1400],
                '준중형': [1400, 1800],
                '중형': [1800, 2400],
                '대형': [2400, 3500],
                'SUV': [2000, 3000],
                '수입차': [2000, 4000]
            }
            
            if car_type in engine_size_map:
                min_engine, max_engine = engine_size_map[car_type]
                engine_size = np.random.randint(min_engine, max_engine + 1)
            else:
                engine_size = 1600
            
            # 7. 자동차번호 (더미)
            car_number = f"{np.random.randint(10,100)}가{np.random.randint(1000,10000)}"
            
            # 8. 현재 보험 가입 상황 및 선호도 분석
            insurance_preferences = self._analyze_insurance_preference(
                age, annual_income, job_risk_level, accident_history, 
                annual_mileage, car_type, driving_experience
            )
            
            driver = {
                'driver_id': f'D{i+1:06d}',
                'birth_date': birth_date,
                'age': age,
                'gender': gender,
                'car_number': car_number,
                'driving_experience': driving_experience,
                'occupation': occupation,
                'job_risk_level': job_risk_level,
                'residence_area': residence_area,
                'annual_income': annual_income,
                'annual_mileage': annual_mileage,
                'accident_history': accident_history,
                'car_brand': car_brand,
                'car_type': car_type,
                'car_year': car_year,
                'car_age': car_age,
                'engine_size': engine_size,
                **insurance_preferences  # 보험 상품별 가입 여부
            }
            
            drivers.append(driver)
            
            if (i + 1) % 2000 == 0:
                print(f"진행률: {i+1}/{n_drivers} ({(i+1)/n_drivers*100:.1f}%)")
        
        return pd.DataFrame(drivers)
    
    def _get_driver_age_distribution(self):
        """운전자 연령 분포 (실제 자동차보험 가입자 기준)"""
        ages = range(20, 70)
        probs = []
        for age in ages:
            if 25 <= age <= 45:
                probs.append(0.025)  # 주력 운전자층
            elif 46 <= age <= 60:
                probs.append(0.02)   # 중년층
            elif 20 <= age < 25:
                probs.append(0.015)  # 젊은 운전자
            else:
                probs.append(0.01)   # 고령 운전자
        
        probs = np.array(probs)
        return probs / probs.sum()
    
    def _analyze_insurance_preference(self, age, income, job_risk, accidents, mileage, car_type, experience):
        """개인 특성 기반 자동차보험 상품 선호도 분석"""
        preferences = {}
        
        for product_key, product_info in self.products.items():
            base_prob = 0.15  # 기본 가입률
            
            # 기본형 (경제성 중시)
            if product_key == 'basic':
                if income < 40000000:  # 저소득
                    base_prob += 0.4
                if age < 25:  # 젊은 운전자 (경제적 부담)
                    base_prob += 0.3
                if car_type in ['경차', '소형']:
                    base_prob += 0.2
                if experience < 3:  # 초보운전자는 기본형부터
                    base_prob += 0.2
            
            # 표준형 (가장 대중적)
            elif product_key == 'standard':
                base_prob += 0.3  # 기본적으로 높은 선호도
                if 30 <= age <= 50:  # 중년층
                    base_prob += 0.2
                if 40000000 <= income <= 70000000:  # 중산층
                    base_prob += 0.2
                if car_type == '준중형':
                    base_prob += 0.15
            
            # 고급형 (안정성 중시)
            elif product_key == 'premium':
                if income > 60000000:  # 고소득
                    base_prob += 0.3
                if age > 35:  # 중년 이상
                    base_prob += 0.2
                if accidents > 0:  # 사고 경험자
                    base_prob += 0.25
                if car_type in ['중형', 'SUV']:
                    base_prob += 0.2
                if job_risk == 'high':  # 고위험 직업
                    base_prob += 0.15
            
            # 프리미엄 (최고 보장)
            elif product_key == 'super_premium':
                if income > 100000000:  # 최고소득층
                    base_prob += 0.4
                if car_type in ['대형', '수입차']:
                    base_prob += 0.3
                if mileage > 30000:  # 고주행자
                    base_prob += 0.2
                if accidents >= 2:  # 다중 사고자
                    base_prob += 0.2
            
            # 소득 수준에 따른 전반적 조정
            if product_key in ['premium', 'super_premium'] and income < 50000000:
                base_prob *= 0.3  # 고급 상품은 소득이 뒷받침되어야
            
            # 최종 가입 확률 조정
            base_prob = max(0.02, min(0.85, base_prob))
            preferences[product_key] = np.random.binomial(1, base_prob)
        
        return preferences
    
    def prepare_training_data(self, df):
        """ML 모델 학습용 데이터 준비"""
        print("자동차보험 학습 데이터 준비 중...")
        
        # 특성 선택 (웹/앱 회원가입시 수집 가능한 정보)
        feature_cols = ['age', 'gender', 'driving_experience', 'occupation', 'residence_area',
                       'annual_income', 'annual_mileage', 'accident_history', 'car_brand',
                       'car_type', 'car_age', 'engine_size']
        
        # 타겟 변수들 (자동차보험 상품별 가입 여부)
        target_cols = list(self.products.keys())
        
        # 데이터 전처리
        processed_df = df[feature_cols + target_cols].copy()
        
        # 범주형 변수 인코딩
        categorical_cols = ['gender', 'occupation', 'residence_area', 'car_brand', 'car_type']
        
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                processed_df[col] = self.label_encoders[col].fit_transform(processed_df[col])
            else:
                processed_df[col] = self.label_encoders[col].transform(processed_df[col])
        
        return processed_df[feature_cols], processed_df[target_cols]
    
    def train_models(self, X, y):
        """자동차보험 추천 모델 및 유사도 모델 학습"""
        print("자동차보험 추천 모델 학습 중...")
        
        # 1. 추천 모델 학습
        base_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        self.recommendation_model = MultiOutputClassifier(base_model)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.recommendation_model.fit(X_train, y_train)
        
        # 성능 평가
        y_pred = self.recommendation_model.predict(X_test)
        
        print("자동차보험 상품별 추천 정확도:")
        for i, product in enumerate(y.columns):
            accuracy = accuracy_score(y_test.iloc[:, i], y_pred[:, i])
            print(f"  {self.products[product]['name']}: {accuracy:.3f}")
        
        # 2. 유사도 모델 학습
        print("유사 운전자 분석 모델 학습 중...")
        X_scaled = self.scaler.fit_transform(X)
        self.similarity_model = NearestNeighbors(n_neighbors=50, metric='cosine')
        self.similarity_model.fit(X_scaled)
        self.user_profiles = X_scaled
        
        print("모델 학습 완료!")
        return X_test, y_test, y_pred
    
    def recommend_car_insurance(self, driver_info: dict) -> dict:
        """새로운 운전자에게 자동차보험 상품 추천"""
        
        # 데이터 전처리
        driver_df = pd.DataFrame([driver_info])
        
        categorical_cols = ['gender', 'occupation', 'residence_area', 'car_brand', 'car_type']
        for col in categorical_cols:
            if col in driver_df.columns and col in self.label_encoders:
                try:
                    driver_df[col] = self.label_encoders[col].transform(driver_df[col])
                except ValueError:
                    driver_df[col] = 0
        
        # 예측 수행
        recommendations = self.recommendation_model.predict_proba(driver_df)
        
        # 결과 정리
        product_recommendations = {}
        for i, (product_key, product_info) in enumerate(self.products.items()):
            probability = recommendations[i][0][1]  # 가입 확률
            
            product_recommendations[product_key] = {
                'name': product_info['name'],
                'description': product_info['description'],
                'coverage': product_info['coverage'],
                'target_customer': product_info['target_customer'],
                'avg_premium': product_info['avg_premium'],
                'probability': probability,
                'recommended': probability > 0.4,  # 40% 이상시 추천
                'confidence': 'high' if probability > 0.7 else 'medium' if probability > 0.5 else 'low'
            }
        
        # 확률 순 정렬
        sorted_recommendations = sorted(product_recommendations.items(), 
                                      key=lambda x: x[1]['probability'], reverse=True)
        
        return {
            'driver_profile': driver_info,
            'recommendations': dict(sorted_recommendations),
            'top_recommendation': sorted_recommendations[0],
            'suitable_products': {k: v for k, v in sorted_recommendations if v[1]['recommended']}
        }
    
    def find_similar_drivers(self, driver_info: dict, n_similar: int = 30) -> dict:
        """유사한 운전자 찾기"""
        
        # 데이터 전처리
        driver_df = pd.DataFrame([driver_info])
        
        categorical_cols = ['gender', 'occupation', 'residence_area', 'car_brand', 'car_type']
        for col in categorical_cols:
            if col in driver_df.columns and col in self.label_encoders:
                try:
                    driver_df[col] = self.label_encoders[col].transform(driver_df[col])
                except ValueError:
                    driver_df[col] = 0
        
        # 정규화 및 유사도 계산
        driver_scaled = self.scaler.transform(driver_df)
        distances, indices = self.similarity_model.kneighbors(driver_scaled)
        
        return {
            'similar_driver_indices': indices[0],
            'similarity_scores': 1 - distances[0],
            'n_similar': n_similar
        }
    
    def analyze_similar_drivers_patterns(self, df, similar_drivers_info: dict) -> dict:
        """유사 운전자들의 자동차보험 가입 패턴 분석"""
        
        similar_indices = similar_drivers_info['similar_driver_indices']
        similar_df = df.iloc[similar_indices].copy()
        
        # 보험 상품별 가입률
        insurance_patterns = {}
        for product_key, product_info in self.products.items():
            join_rate = similar_df[product_key].mean()
            join_count = similar_df[product_key].sum()
            
            insurance_patterns[product_key] = {
                'name': product_info['name'],
                'join_rate': join_rate,
                'join_count': int(join_count),
                'total_drivers': len(similar_df),
                'avg_premium': product_info['avg_premium']
            }
        
        # 운전자 특성 분석
        driver_characteristics = {
            'age_range': f"{similar_df['age'].min()}~{similar_df['age'].max()}세",
            'avg_age': similar_df['age'].mean(),
            'avg_experience': similar_df['driving_experience'].mean(),
            'avg_mileage': similar_df['annual_mileage'].mean(),
            'avg_income': similar_df['annual_income'].mean(),
            'accident_rate': (similar_df['accident_history'] > 0).mean(),
            'gender_distribution': similar_df['gender'].value_counts().to_dict(),
            'popular_car_types': similar_df['car_type'].value_counts().head(3).to_dict(),
            'region_distribution': similar_df['residence_area'].value_counts().head(3).to_dict()
        }
        
        return {
            'insurance_patterns': insurance_patterns,
            'driver_characteristics': driver_characteristics,
            'total_similar_drivers': len(similar_df)
        }

# 시스템 실행
print("\n=== 자동차보험 추천 시스템 초기화 ===")

# 1. 시스템 초기화
car_recommender = CarInsuranceRecommendationSystem()

# 2. 운전자 데이터 생성
driver_data = car_recommender.generate_driver_data(n_drivers=12000)
print(f"\n생성된 운전자 데이터: {driver_data.shape}")
print("\n운전자 데이터 샘플:")
print(driver_data.head(3))

# 3. 학습 데이터 준비 및 모델 학습
X, y = car_recommender.prepare_training_data(driver_data)
X_test, y_test, y_pred = car_recommender.train_models(X, y)

print("\n=== 자동차보험 상품별 가입 현황 분석 ===")

# 상품별 가입률 분석
for product_key, product_info in CAR_INSURANCE_PRODUCTS.items():
    rate = driver_data[product_key].mean()
    count = driver_data[product_key].sum()
    print(f"{product_info['name']}: {rate:.1%} ({count:,}명)")

# 시각화
plt.figure(figsize=(20, 15))

# 1) 자동차보험 상품별 가입률
plt.subplot(3, 4, 1)
products = [info['name'].replace('자동차보험 ', '') for info in CAR_INSURANCE_PRODUCTS.values()]
rates = [driver_data[key].mean() for key in CAR_INSURANCE_PRODUCTS.keys()]
colors = ['lightblue', 'lightgreen', 'orange', 'red']
plt.bar(products, rates, color=colors)
plt.title('자동차보험 상품별 가입률')
plt.xticks(rotation=45)
plt.ylabel('가입률')

# 2) 연령대별 상품 선호도
plt.subplot(3, 4, 2)
age_groups = pd.cut(driver_data['age'], bins=[20, 30, 40, 50, 60, 70], 
                   labels=['20대', '30대', '40대', '50대', '60대'])

for i, (product_key, product_info) in enumerate(CAR_INSURANCE_PRODUCTS.items()):
    product_by_age = driver_data.groupby(age_groups)[product_key].mean()
    plt.plot(range(len(product_by_age)), product_by_age.values, 
             marker='o', label=product_info['name'].replace('자동차보험 ', ''), color=colors[i])

plt.title('연령대별 상품 선호도')
plt.xticks(range(5), ['20대', '30대', '40대', '50대', '60대'])
plt.legend()
plt.ylabel('가입률')

# 3) 소득별 상품 선호도
plt.subplot(3, 4, 3)
income_groups = pd.cut(driver_data['annual_income'], 
                      bins=[0, 40000000, 60000000, 80000000, float('inf')],
                      labels=['4천만원 이하', '4-6천만원', '6-8천만원', '8천만원 이상'])

basic_by_income = driver_data.groupby(income_groups)['basic'].mean()
premium_by_income = driver_data.groupby(income_groups)['premium'].mean()
super_premium_by_income = driver_data.groupby(income_groups)['super_premium'].mean()

x = range(len(basic_by_income))
plt.plot(x, basic_by_income.values, marker='o', label='기본형', color='lightblue')
plt.plot(x, premium_by_income.values, marker='s', label='고급형', color='orange')
plt.plot(x, super_premium_by_income.values, marker='^', label='프리미엄', color='red')
plt.xticks(x, basic_by_income.index, rotation=45)
plt.title('소득별 상품 선호도')
plt.legend()
plt.ylabel('가입률')

# 4) 사고이력별 상품 선택
plt.subplot(3, 4, 4)
accident_groups = driver_data.groupby('accident_history')[['basic', 'standard', 'premium', 'super_premium']].mean()
accident_groups.plot(kind='bar', ax=plt.gca(), color=colors)
plt.title('사고이력별 상품 선택')
plt.xlabel('사고 횟수')
plt.ylabel('가입률')
plt.legend(['기본형', '표준형', '고급형', '프리미엄'])
plt.xticks(rotation=0)

# 5) 차종별 보험 선호도
plt.subplot(3, 4, 5)
car_type_insurance = driver_data.groupby('car_type')[['basic', 'premium', 'super_premium']].mean()
car_type_insurance.plot(kind='bar', ax=plt.gca())
plt.title('차종별 보험 선호도')
plt.xticks(rotation=45)
plt.legend(['기본형', '고급형', '프리미엄'])

# 6) 주행거리별 보험료 부담도
plt.subplot(3, 4, 6)
mileage_groups = pd.cut(driver_data['annual_mileage'], 
                       bins=[0, 10000, 20000, 30000, float('inf')],
                       labels=['1만km 이하', '1-2만km', '2-3만km', '3만km 이상'])
mileage_premium = driver_data.groupby(mileage_groups)[['premium', 'super_premium']].mean()
mileage_premium.plot(kind='bar', ax=plt.gca())
plt.title('주행거리별 고급 상품 선호도')
plt.xticks(rotation=45)
plt.legend(['고급형', '프리미엄'])

# 7) 지역별 보험 가입률
plt.subplot(3, 4, 7)
region_standard = driver_data.groupby('residence_area')['standard'].mean().sort_values(ascending=False)
region_standard.head(8).plot(kind='bar', color='lightgreen')
plt.title('지역별 표준형 가입률 (상위 8개)')
plt.xticks(rotation=45)

# 8) 직업별 보험 선호도
plt.subplot(3, 4, 8)
job_insurance = driver_data.groupby('occupation')[['basic', 'standard', 'premium']].mean()
job_insurance.plot(kind='bar', ax=plt.gca(), width=0.8)
plt.title('직업별 보험 선호도')
plt.xticks(rotation=45)
plt.legend(['기본형', '표준형', '고급형'])

# 9) 운전경력별 상품 선택
plt.subplot(3, 4, 9)
experience_groups = pd.cut(driver_data['driving_experience'], 
                          bins=[0, 3, 10, 20, float('inf')],
                          labels=['초보(3년 이하)', '일반(3-10년)', '베테랑(10-20년)', '고수(20년 이상)'])
exp_insurance = driver_data.groupby(experience_groups)[['basic', 'standard', 'premium']].mean()
exp_insurance.plot(kind='bar', ax=plt.gca())
plt.title('운전경력별 상품 선택')
plt.xticks(rotation=45)
plt.legend(['기본형', '표준형', '고급형'])

# 10) 차량 연식별 보험 선택
plt.subplot(3, 4, 10)
age_groups = pd.cut(driver_data['car_age'], 
                   bins=[0, 3, 7, 15, float('inf')],
                   labels=['신차(3년 이하)', '준신차(3-7년)', '중고차(7-15년)', '노후차(15년 이상)'])
car_age_insurance = driver_data.groupby(age_groups)[['basic', 'standard', 'premium']].mean()
car_age_insurance.plot(kind='bar', ax=plt.gca())
plt.title('차량 연식별 보험 선택')
plt.xticks(rotation=45)
plt.legend(['기본형', '표준형', '고급형'])

# 11) 성별 보험 선호도
plt.subplot(3, 4, 11)
gender_insurance = driver_data.groupby('gender')[['basic', 'standard', 'premium', 'super_premium']].mean()
gender_insurance.plot(kind='bar', ax=plt.gca(), color=colors)
plt.title('성별 보험 선호도')
plt.xticks([0, 1], ['여성', '남성'], rotation=0)
plt.legend(['기본형', '표준형', '고급형', '프리미엄'])

# 12) 상품간 상관관계
plt.subplot(3, 4, 12)
product_cols = list(CAR_INSURANCE_PRODUCTS.keys())
corr_matrix = driver_data[product_cols].corr()
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, square=True)
plt.title('자동차보험 상품간 상관관계')

plt.tight_layout()
plt.show()

print("\n=== 자동차보험 추천 테스트 ===")

# 테스트용 운전자들
test_drivers = [
    {
        'age': 26,
        'gender': 'M',
        'driving_experience': 3,
        'occupation': '사무직',
        'residence_area': '서울',
        'annual_income': 35000000,
        'annual_mileage': 8000,
        'accident_history': 0,
        'car_brand': '현대',
        'car_type': '소형',
        'car_age': 2,
        'engine_size': 1400
    },
    {
        'age': 38,
        'gender': 'F',
        'driving_experience': 15,
        'occupation': '전문직',
        'residence_area': '경기',
        'annual_income': 85000000,
        'annual_mileage': 15000,
        'accident_history': 1,
        'car_brand': '벤츠',
        'car_type': '중형',
        'car_age': 1,
        'engine_size': 2000
    },
    {
        'age': 55,
        'gender': 'M',
        'driving_experience': 30,
        'occupation': '운수업',
        'residence_area': '부산',
        'annual_income': 45000000,
        'annual_mileage': 35000,
        'accident_history': 2,
        'car_brand': '현대',
        'car_type': 'SUV',
        'car_age': 5,
        'engine_size': 2400
    }
]

for i, driver in enumerate(test_drivers, 1):
    print(f"\n=== 테스트 운전자 {i} ===")
    print(f"프로필: {driver['age']}세 {driver['gender']}, {driver['occupation']}")
    print(f"차량: {driver['car_brand']} {driver['car_type']} ({driver['car_age']}년차)")
    print(f"연간주행: {driver['annual_mileage']:,}km, 사고이력: {driver['accident_history']}회")
    
    # 1. 개인 맞춤 자동차보험 추천
    recommendations = car_recommender.recommend_car_insurance(driver)
    
    print(f"\n🎯 추천 자동차보험:")
    top_product = recommendations['top_recommendation']
    print(f"최우선 추천: {top_product[1]['name']} (가입확률: {top_product[1]['probability']:.1%})")
    print(f"추천 이유: {top_product[1]['target_customer']}")
    print(f"예상 보험료: {top_product[1]['avg_premium']:,}원/년")
    
    print(f"\n모든 상품 추천도:")
    for product_key, rec_info in recommendations['recommendations'].items():
        status = "✅" if rec_info['recommended'] else "❌"
        confidence = rec_info['confidence']
        print(f"  {rec_info['name']}: {rec_info['probability']:.1%} {status} ({confidence})")
    
    # 2. 유사 운전자 분석
    similar_drivers = car_recommender.find_similar_drivers(driver, n_similar=50)
    similar_analysis = car_recommender.analyze_similar_drivers_patterns(driver_data, similar_drivers)
    
    print(f"\n👥 유사 운전자 분석 (상위 50명):")
    chars = similar_analysis['driver_characteristics']
    print(f"  평균 연령: {chars['avg_age']:.1f}세")
    print(f"  평균 경력: {chars['avg_experience']:.1f}년")
    print(f"  평균 주행거리: {chars['avg_mileage']:,.0f}km")
    print(f"  평균 소득: {chars['avg_income']:,.0f}원")
    print(f"  사고 경험률: {chars['accident_rate']:.1%}")
    
    print(f"\n유사 운전자들의 자동차보험 선택 패턴:")
    sorted_patterns = sorted(similar_analysis['insurance_patterns'].items(), 
                           key=lambda x: x[1]['join_rate'], reverse=True)
    
    for product_key, stats in sorted_patterns:
        print(f"  {stats['name']}: {stats['join_rate']:.1%} "
              f"({stats['join_count']}/{stats['total_drivers']}명)")

print("\n=== 자동차보험 시장 인사이트 ===")

# 시장 분석
total_drivers = len(driver_data)
print(f"분석 대상: {total_drivers:,}명의 운전자")

print(f"\n📊 상품별 시장 점유율:")
for product_key, product_info in CAR_INSURANCE_PRODUCTS.items():
    rate = driver_data[product_key].mean()
    market_size = driver_data[product_key].sum()
    revenue = market_size * product_info['avg_premium']
    print(f"  {product_info['name']}: {rate:.1%} ({market_size:,}명, 예상매출: {revenue/100000000:.1f}억원)")

# 고객 세그먼트 분석
print(f"\n🎯 주요 고객 세그먼트:")

# 젊은 운전자 (20-30대)
young_drivers = driver_data[driver_data['age'] < 30]
print(f"젊은 운전자(20대): {len(young_drivers):,}명 ({len(young_drivers)/total_drivers:.1%})")
print(f"  선호 상품: 기본형 {young_drivers['basic'].mean():.1%}, 표준형 {young_drivers['standard'].mean():.1%}")

# 중년 운전자 (30-50대)
middle_drivers = driver_data[(driver_data['age'] >= 30) & (driver_data['age'] < 50)]
print(f"중년 운전자(30-40대): {len(middle_drivers):,}명 ({len(middle_drivers)/total_drivers:.1%})")
print(f"  선호 상품: 표준형 {middle_drivers['standard'].mean():.1%}, 고급형 {middle_drivers['premium'].mean():.1%}")

# 고소득 운전자
high_income = driver_data[driver_data['annual_income'] > 80000000]
print(f"고소득 운전자(8천만원 이상): {len(high_income):,}명 ({len(high_income)/total_drivers:.1%})")
print(f"  선호 상품: 고급형 {high_income['premium'].mean():.1%}, 프리미엄 {high_income['super_premium'].mean():.1%}")

print("\n=== 실제 서비스 API 구현 예시 ===")

def get_car_insurance_recommendation_api(driver_profile: dict) -> dict:
    """
    실제 웹/앱에서 호출할 자동차보험 추천 API
    """
    try:
        # 1. 개인 맞춤 추천
        personal_rec = car_recommender.recommend_car_insurance(driver_profile)
        
        # 2. 유사 운전자 분석
        similar_drivers = car_recommender.find_similar_drivers(driver_profile, n_similar=30)
        similar_patterns = car_recommender.analyze_similar_drivers_patterns(driver_data, similar_drivers)
        
        # 3. API 응답 구성
        api_response = {
            'status': 'success',
            'driver_profile': driver_profile,
            'recommendations': {
                'primary_recommendation': {
                    'product': personal_rec['top_recommendation'][1]['name'],
                    'probability': personal_rec['top_recommendation'][1]['probability'],
                    'description': personal_rec['top_recommendation'][1]['description'],
                    'estimated_premium': personal_rec['top_recommendation'][1]['avg_premium'],
                    'coverage': personal_rec['top_recommendation'][1]['coverage'],
                    'confidence': personal_rec['top_recommendation'][1]['confidence']
                },
                'all_products': []
            },
            'similar_drivers_insight': {
                'total_analyzed': similar_patterns['total_similar_drivers'],
                'demographics': similar_patterns['driver_characteristics'],
                'popular_choices': []
            },
            'market_position': {
                'age_group_preference': '해당 연령대 선호 상품 분석',
                'income_bracket_trend': '소득 구간별 트렌드',
                'regional_preference': '지역별 선호도'
            }
        }
        
        # 모든 상품 정보 추가
        for product_key, rec_info in personal_rec['recommendations'].items():
            api_response['recommendations']['all_products'].append({
                'product_name': rec_info['name'],
                'probability': rec_info['probability'],
                'recommended': rec_info['recommended'],
                'estimated_premium': rec_info['avg_premium'],
                'confidence': rec_info['confidence']
            })
        
        # 유사 운전자들의 인기 선택 추가
        for product_key, pattern in similar_patterns['insurance_patterns'].items():
            api_response['similar_drivers_insight']['popular_choices'].append({
                'product_name': pattern['name'],
                'adoption_rate': pattern['join_rate'],
                'user_count': pattern['join_count']
            })
        
        return api_response
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'추천 처리 중 오류: {str(e)}',
            'error_code': 'RECOMMENDATION_ERROR'
        }

# API 테스트
test_driver_api = {
    'age': 32,
    'gender': 'M',
    'driving_experience': 8,
    'occupation': '사무직',
    'residence_area': '서울',
    'annual_income': 55000000,
    'annual_mileage': 12000,
    'accident_history': 0,
    'car_brand': '현대',
    'car_type': '준중형',
    'car_age': 3,
    'engine_size': 1600
}

api_result = get_car_insurance_recommendation_api(test_driver_api)

print("=== API 응답 예시 ===")
print(f"상태: {api_result['status']}")
print(f"\n주 추천 상품: {api_result['recommendations']['primary_recommendation']['product']}")
print(f"가입 확률: {api_result['recommendations']['primary_recommendation']['probability']:.1%}")
print(f"예상 보험료: {api_result['recommendations']['primary_recommendation']['estimated_premium']:,}원/년")

print(f"\n유사 운전자 분석:")
print(f"분석 대상: {api_result['similar_drivers_insight']['total_analyzed']}명")
print(f"평균 연령: {api_result['similar_drivers_insight']['demographics']['avg_age']:.1f}세")

print(f"\n인기 상품 순위:")
popular_products = sorted(api_result['similar_drivers_insight']['popular_choices'], 
                         key=lambda x: x['adoption_rate'], reverse=True)
for i, product in enumerate(popular_products[:3], 1):
    print(f"  {i}. {product['product_name']}: {product['adoption_rate']:.1%}")

print("\n=== 시스템 성능 요약 ===")
print(f"✅ 학습 데이터: {len(driver_data):,}명의 운전자")
print(f"✅ 자동차보험 상품: {len(CAR_INSURANCE_PRODUCTS)}개")
print(f"✅ 개인 맞춤 추천 기능")
print(f"✅ 유사 운전자 분석 기능")
print(f"✅ 실시간 API 서비스 준비 완료")
print(f"✅ Django Mock 서버 연동 가능")

print("\n=== 다음 단계 ===")
print("1. 🚀 Django REST API 엔드포인트 구현")
print("2. 📱 웹/모바일 앱 프론트엔드 연동")
print("3. 💾 Redis를 통한 실시간 캐싱")
print("4. 📊 A/B 테스트를 통한 추천 성능 개선")
print("5. 🔄 실제 보험사 API 연동")
print("6. 📈 사용자 피드백 기반 모델 재학습")