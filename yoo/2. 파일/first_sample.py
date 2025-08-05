# Django 보험 서버 연동 - 자동차보험 가입 예측 ML 모델
# Mock 서버의 보험료 계산 로직을 활용한 실제적인 가입 예측 모델

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import random
import warnings
from typing import Dict, List, Any
warnings.filterwarnings('ignore')

# Mock 서버에서 사용하는 11개 보험사 정보 (실제 코드와 동일)
INSURANCE_COMPANIES = {
    '삼성화재': {'base_rate': 850000, 'market_share': 15.8},
    '현대해상': {'base_rate': 820000, 'market_share': 14.2},
    'KB손해보험': {'base_rate': 780000, 'market_share': 12.5},
    '메리츠화재': {'base_rate': 800000, 'market_share': 11.3},
    'DB손해보험': {'base_rate': 760000, 'market_share': 9.8},
    '롯데손해보험': {'base_rate': 790000, 'market_share': 8.7},
    '하나손해보험': {'base_rate': 830000, 'market_share': 7.9},
    '흥국화재': {'base_rate': 770000, 'market_share': 6.5},
    'AXA손해보험': {'base_rate': 810000, 'market_share': 5.8},
    'MG손해보험': {'base_rate': 750000, 'market_share': 4.2},
    '캐롯손해보험': {'base_rate': 740000, 'market_share': 3.3}
}

# 시드 고정
np.random.seed(42)
random.seed(42)

print("=== Django 보험 서버 연동 - 자동차보험 가입 예측 ML 모델 ===")
print("Mock 서버의 실제 보험료 계산 로직을 반영한 데이터 생성")

class InsuranceMLDataGenerator:
    """Mock 서버 로직을 기반으로 한 ML용 데이터 생성기"""
    
    def __init__(self):
        self.companies = INSURANCE_COMPANIES
        
    def get_age_category(self, birth_date: str) -> tuple:
        """생년월일로 나이와 연령대 계산"""
        try:
            birth = datetime.strptime(birth_date, '%Y-%m-%d')
            age = (datetime.now() - birth).days // 365
            
            if age < 26:
                return age, 'young'
            elif age <= 50:
                return age, 'middle'
            else:
                return age, 'senior'
        except:
            return 35, 'middle'

    def calculate_risk_score(self, user_profile: dict) -> float:
        """Mock 서버와 동일한 위험도 계산 로직"""
        risk_score = 0
        
        birth_date = user_profile.get('birth_date', '1990-01-01')
        age, age_category = self.get_age_category(birth_date)
        
        # 나이별 위험도 (Mock 서버 로직 반영)
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
            
        return max(0, risk_score)

    def calculate_expected_premium(self, user_profile: dict) -> dict:
        """Mock 서버의 보험료 계산 로직을 간소화한 버전"""
        birth_date = user_profile.get('birth_date', '1990-01-01')
        age, age_category = self.get_age_category(birth_date)
        gender = user_profile.get('gender', 'M')
        region = user_profile.get('residence_area', '서울')
        driving_experience = user_profile.get('driving_experience', 5)
        accident_history = user_profile.get('accident_history', 0)
        car_type = user_profile.get('car_type', '준중형')
        annual_mileage = user_profile.get('annual_mileage', 12000)
        
        # 평균 기본료 계산
        avg_base_rate = np.mean([info['base_rate'] for info in self.companies.values()])
        
        # 요율 적용 (Mock 서버 로직 반영)
        age_multipliers = {'young': 1.3, 'middle': 1.0, 'senior': 0.87}
        gender_multipliers = {'M': 1.0, 'F': 0.92}
        region_multipliers = {'서울': 1.1, '부산': 0.95, '대구': 0.9, '경기': 1.05}
        car_multipliers = {'경차': 0.8, '소형': 0.9, '준중형': 1.0, '중형': 1.15, '대형': 1.3, 'SUV': 1.2}
        
        age_mult = age_multipliers.get(age_category, 1.0)
        gender_mult = gender_multipliers.get(gender, 1.0)
        region_mult = region_multipliers.get(region, 0.9)
        car_mult = car_multipliers.get(car_type, 1.0)
        
        # 경력 할인
        experience_discount = min(driving_experience * 0.045, 0.5)
        
        # 사고 할증
        accident_penalty = accident_history * 0.25
        
        # 주행거리 조정
        if annual_mileage < 5000:
            mileage_mult = 0.85
        elif annual_mileage > 20000:
            mileage_mult = 1.15
        else:
            mileage_mult = 1.0
        
        # 최종 보험료 계산
        final_premium = (
            avg_base_rate * age_mult * gender_mult * region_mult * 
            car_mult * mileage_mult * (1 - experience_discount) * (1 + accident_penalty)
        )
        
        return {
            'expected_premium': int(final_premium),
            'monthly_premium': int(final_premium / 12 * 1.05),
            'risk_level': 'high' if final_premium > 1000000 else 'medium' if final_premium > 700000 else 'low'
        }

    def generate_realistic_data(self, n_samples=10000):
        """Mock 서버 로직을 반영한 현실적인 데이터 생성"""
        data = []
        
        for i in range(n_samples):
            # 1. 기본 정보 생성
            age = np.random.choice(range(20, 71), p=self._get_age_distribution())
            birth_year = 2024 - age
            birth_date = f"{birth_year}-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d}"
            
            gender = np.random.choice(['M', 'F'], p=[0.55, 0.45])
            
            # 2. 지역 (실제 인구 분포 반영)
            regions = ['서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산', '기타']
            region_probs = [0.19, 0.25, 0.07, 0.05, 0.06, 0.03, 0.03, 0.02, 0.30]
            residence_area = np.random.choice(regions, p=region_probs)
            
            # 3. 운전경력 (나이와 상관관계)
            max_experience = max(0, age - 18)
            driving_experience = min(max_experience, 
                                   max(0, int(np.random.exponential(max_experience/3))))
            
            # 4. 직업 (Mock 서버의 위험도 분류 반영)
            job_categories = {
                'high_risk': ['운수업', '건설업', '제조업', '배달업'],
                'medium_risk': ['서비스업', '자영업', '영업직', '기능직'],
                'low_risk': ['사무직', '공무원', '교육직', '의료진', '금융업', '전문직']
            }
            
            risk_probs = [0.2, 0.35, 0.45]  # 고위험, 중위험, 저위험
            job_risk = np.random.choice(['high_risk', 'medium_risk', 'low_risk'], p=risk_probs)
            occupation = np.random.choice(job_categories[job_risk])
            
            # 5. 차량 정보
            car_types = ['경차', '소형', '준중형', '중형', '대형', 'SUV']
            car_type_probs = [0.15, 0.25, 0.30, 0.20, 0.05, 0.05]
            car_type = np.random.choice(car_types, p=car_type_probs)
            
            car_brands = list(INSURANCE_COMPANIES.keys())[:5]  # 주요 5개 브랜드
            car_brand = np.random.choice(['현대', '기아', '제네시스', '벤츠', 'BMW', '기타'], 
                                       p=[0.35, 0.25, 0.08, 0.08, 0.06, 0.18])
            
            car_year = np.random.choice(range(2015, 2025), 
                                      p=[0.05, 0.05, 0.08, 0.10, 0.12, 0.15, 0.15, 0.15, 0.10, 0.05])
            car_age = 2024 - car_year
            
            # 6. 주행거리 (직업, 지역과 상관관계)
            base_mileage = np.random.lognormal(9.4, 0.6)  # 평균 약 12,000km
            
            # 직업별 조정
            job_multipliers = {'high_risk': 1.4, 'medium_risk': 1.1, 'low_risk': 0.9}
            mileage_mult = job_multipliers[job_risk]
            
            # 지역별 조정
            if residence_area in ['서울', '부산', '대구', '인천']:
                mileage_mult *= 0.8  # 대도시는 적게
            else:
                mileage_mult *= 1.2  # 지방은 많게
                
            annual_mileage = int(base_mileage * mileage_mult)
            annual_mileage = max(3000, min(50000, annual_mileage))  # 현실적 범위로 제한
            
            # 7. 사고이력 (나이, 경력, 주행거리와 상관관계)
            accident_prob = (
                0.02 +  # 기본 확률
                max(0, (30 - age) * 0.001) +  # 젊을수록 위험
                (annual_mileage / 100000) * 0.03 +  # 주행거리
                max(0, (5 - driving_experience) * 0.005)  # 경력 부족
            )
            accident_history = np.random.poisson(accident_prob * 3)  # 최근 3년
            accident_history = min(5, accident_history)  # 최대 5회
            
            # 8. 자동차 번호 (더미)
            car_number = f"{np.random.randint(10,100)}가{np.random.randint(1000,10000)}"
            
            # 사용자 프로필 생성
            user_profile = {
                'birth_date': birth_date,
                'gender': gender,
                'residence_area': residence_area,
                'driving_experience': driving_experience,
                'accident_history': accident_history,
                'annual_mileage': annual_mileage,
                'car_type': car_type
            }
            
            # 위험도 및 예상 보험료 계산
            risk_score = self.calculate_risk_score(user_profile)
            premium_info = self.calculate_expected_premium(user_profile)
            
            # 9. 보험 가입 확률 계산 (현실적인 요소들 반영)
            base_prob = 0.25  # 기본 25% 가입률
            
            # 나이별 조정 (나이 많을수록 가입률 증가)
            age_factor = (age - 20) * 0.008
            
            # 사고이력별 조정 (사고 많을수록 가입 필요성 증가)
            accident_factor = accident_history * 0.08
            
            # 위험도별 조정
            risk_factor = risk_score * 0.03
            
            # 보험료 부담 고려 (너무 비싸면 가입률 감소)
            if premium_info['expected_premium'] > 1200000:
                price_factor = -0.1
            elif premium_info['expected_premium'] < 600000:
                price_factor = 0.05
            else:
                price_factor = 0
            
            # 소득 수준 추정 (직업 기반)
            income_factors = {'high_risk': -0.05, 'medium_risk': 0, 'low_risk': 0.08}
            income_factor = income_factors[job_risk]
            
            # 최종 가입 확률
            join_prob = base_prob + age_factor + accident_factor + risk_factor + price_factor + income_factor
            join_prob = max(0.05, min(0.85, join_prob))  # 5%~85% 범위로 제한
            
            # 실제 가입 여부 결정
            insurance_subscription = np.random.binomial(1, join_prob)
            
            # 데이터 행 생성
            row = {
                'birth_date': birth_date,
                'age': age,
                'gender': gender,
                'car_number': car_number,
                'driving_experience': driving_experience,
                'occupation': occupation,
                'job_risk_level': job_risk,
                'residence_area': residence_area,
                'annual_mileage': annual_mileage,
                'accident_history': accident_history,
                'car_brand': car_brand,
                'car_type': car_type,
                'car_year': car_year,
                'car_age': car_age,
                'risk_score': risk_score,
                'expected_premium': premium_info['expected_premium'],
                'monthly_premium': premium_info['monthly_premium'],
                'risk_level': premium_info['risk_level'],
                'join_probability': join_prob,
                'insurance_subscription': insurance_subscription  # 타겟 변수
            }
            
            data.append(row)
            
            # 진행상황 출력
            if (i + 1) % 2000 == 0:
                print(f"데이터 생성 진행: {i+1}/{n_samples} ({(i+1)/n_samples*100:.1f}%)")
        
        return pd.DataFrame(data)
    
    def _get_age_distribution(self):
        """현실적인 운전자 나이 분포"""
        ages = range(20, 71)
        probs = []
        for age in ages:
            if 25 <= age <= 45:
                probs.append(0.025)  # 주력 연령대
            elif 46 <= age <= 60:
                probs.append(0.020)  # 중년층
            elif 20 <= age < 25:
                probs.append(0.015)  # 젊은층
            else:
                probs.append(0.010)  # 고령층
        
        probs = np.array(probs)
        return probs / probs.sum()

# 데이터 생성
print("\n1단계: Mock 서버 로직 기반 데이터 생성")
generator = InsuranceMLDataGenerator()
df = generator.generate_realistic_data(n_samples=10000)

print(f"\n생성 완료! 데이터 크기: {df.shape}")
print("\n생성된 데이터 샘플:")
print(df.head())

print(f"\n보험 가입률: {df['insurance_subscription'].mean():.1%}")
print(f"평균 예상 보험료: {df['expected_premium'].mean():,.0f}원")

# EDA 및 시각화
print("\n2단계: 탐색적 데이터 분석")

# 기본 통계
print("\n=== 기본 통계 정보 ===")
print(df.describe())

print("\n=== 범주형 변수 분포 ===")
categorical_cols = ['gender', 'job_risk_level', 'residence_area', 'car_type', 'risk_level']
for col in categorical_cols:
    print(f"\n{col}:")
    print(df[col].value_counts())

# 시각화
plt.figure(figsize=(20, 16))

# 1) 나이별 보험 가입률
plt.subplot(4, 4, 1)
age_groups = pd.cut(df['age'], bins=[20, 30, 40, 50, 60, 70], labels=['20대', '30대', '40대', '50대', '60대'])
age_join_rate = df.groupby(age_groups)['insurance_subscription'].mean()
age_join_rate.plot(kind='bar', color='skyblue')
plt.title('연령대별 보험 가입률')
plt.xticks(rotation=45)

# 2) 성별 가입률
plt.subplot(4, 4, 2)
gender_join = df.groupby('gender')['insurance_subscription'].mean()
gender_join.plot(kind='bar', color=['lightcoral', 'lightblue'])
plt.title('성별 보험 가입률')
plt.xticks(rotation=0)

# 3) 직업 위험도별 가입률
plt.subplot(4, 4, 3)
job_join = df.groupby('job_risk_level')['insurance_subscription'].mean()
job_join.plot(kind='bar', color='lightgreen')
plt.title('직업 위험도별 가입률')
plt.xticks(rotation=45)

# 4) 사고이력별 가입률
plt.subplot(4, 4, 4)
accident_join = df.groupby('accident_history')['insurance_subscription'].mean()
accident_join.plot(kind='bar', color='orange')
plt.title('사고이력별 가입률')

# 5) 예상 보험료 분포
plt.subplot(4, 4, 5)
plt.hist(df['expected_premium'], bins=50, alpha=0.7, color='purple')
plt.title('예상 보험료 분포')
plt.xlabel('보험료(원)')

# 6) 차종별 가입률
plt.subplot(4, 4, 6)
car_join = df.groupby('car_type')['insurance_subscription'].mean()
car_join.plot(kind='bar', color='gold')
plt.title('차종별 가입률')
plt.xticks(rotation=45)

# 7) 지역별 가입률
plt.subplot(4, 4, 7)
region_join = df.groupby('residence_area')['insurance_subscription'].mean().sort_values(ascending=False)
region_join.plot(kind='bar', color='pink')
plt.title('지역별 가입률')
plt.xticks(rotation=45)

# 8) 위험도 점수별 가입률
plt.subplot(4, 4, 8)
plt.scatter(df['risk_score'], df['insurance_subscription'], alpha=0.5)
plt.title('위험도 점수 vs 가입 여부')
plt.xlabel('위험도 점수')

# 9) 보험료와 가입률 관계
plt.subplot(4, 4, 9)
premium_bins = pd.cut(df['expected_premium'], bins=10)
premium_join = df.groupby(premium_bins)['insurance_subscription'].mean()
premium_join.plot(kind='line', marker='o')
plt.title('보험료 구간별 가입률')
plt.xticks(rotation=45)

# 10) 운전경력별 가입률
plt.subplot(4, 4, 10)
exp_join = df.groupby('driving_experience')['insurance_subscription'].mean()
exp_join.plot(kind='line', marker='o', color='red')
plt.title('운전경력별 가입률')

# 11) 상관관계 히트맵
plt.subplot(4, 4, 11)
numeric_cols = ['age', 'driving_experience', 'annual_mileage', 'accident_history', 
               'car_age', 'risk_score', 'expected_premium', 'insurance_subscription']
corr_matrix = df[numeric_cols].corr()
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, square=True, cbar_kws={'shrink': 0.8})
plt.title('변수간 상관관계')

# 12) 가입 여부별 보험료 분포
plt.subplot(4, 4, 12)
df[df['insurance_subscription']==1]['expected_premium'].hist(alpha=0.7, label='가입', bins=30)
df[df['insurance_subscription']==0]['expected_premium'].hist(alpha=0.7, label='미가입', bins=30)
plt.title('가입 여부별 보험료 분포')
plt.legend()

plt.tight_layout()
plt.show()

# 머신러닝 모델링
print("\n3단계: 머신러닝 모델 학습")

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import GridSearchCV

# 특성 선택 (Mock 서버 입력값과 매칭)
feature_cols = ['age', 'gender', 'driving_experience', 'job_risk_level', 'residence_area', 
               'annual_mileage', 'accident_history', 'car_type', 'car_age', 'expected_premium']

# 데이터 전처리
model_df = df[feature_cols + ['insurance_subscription']].copy()

# 범주형 변수 인코딩
label_encoders = {}
categorical_cols = ['gender', 'job_risk_level', 'residence_area', 'car_type']

for col in categorical_cols:
    le = LabelEncoder()
    model_df[col] = le.fit_transform(model_df[col])
    label_encoders[col] = le

print("전처리 완료!")
print(model_df.head())

# 특성과 타겟 분리
X = model_df.drop('insurance_subscription', axis=1)
y = model_df['insurance_subscription']

# 학습/테스트 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"학습 데이터: {X_train.shape}, 테스트 데이터: {X_test.shape}")

# 모델들 학습 및 비교
models = {
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(random_state=42),
    'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000)
}

model_results = {}

for name, model in models.items():
    print(f"\n{name} 학습 중...")
    
    if name == 'Logistic Regression':
        # 로지스틱 회귀는 스케일링 필요
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    else:
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # 성능 평가
    auc_score = roc_auc_score(y_test, y_pred_proba)
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
    
    model_results[name] = {
        'model': model,
        'auc': auc_score,
        'cv_mean': cv_scores.mean(),
        'cv_std': cv_scores.std(),
        'predictions': y_pred,
        'probabilities': y_pred_proba
    }
    
    print(f"AUC Score: {auc_score:.4f}")
    print(f"CV AUC: {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")

# 최고 성능 모델 선택
best_model_name = max(model_results.keys(), key=lambda x: model_results[x]['auc'])
best_model = model_results[best_model_name]['model']

print(f"\n최고 성능 모델: {best_model_name}")
print(f"AUC: {model_results[best_model_name]['auc']:.4f}")

# 특성 중요도 (Random Forest의 경우)
if best_model_name == 'Random Forest':
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n특성 중요도:")
    print(feature_importance)

# 최종 성능 리포트
print(f"\n=== {best_model_name} 최종 성능 리포트 ===")
print(classification_report(y_test, model_results[best_model_name]['predictions']))

# 시각화
plt.figure(figsize=(15, 10))

# 1) 모델 비교
plt.subplot(2, 3, 1)
model_names = list(model_results.keys())
auc_scores = [model_results[name]['auc'] for name in model_names]
plt.bar(model_names, auc_scores, color=['skyblue', 'lightgreen', 'lightcoral'])
plt.title('모델별 AUC 점수')
plt.xticks(rotation=45)
plt.ylabel('AUC Score')

# 2) ROC 커브
plt.subplot(2, 3, 2)
for name in model_names:
    fpr, tpr, _ = roc_curve(y_test, model_results[name]['probabilities'])
    plt.plot(fpr, tpr, label=f"{name} (AUC={model_results[name]['auc']:.3f})")
plt.plot([0, 1], [0, 1], 'k--')
plt.title('ROC Curves')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.legend()

# 3) 특성 중요도 (Random Forest)
if best_model_name == 'Random Forest':
    plt.subplot(2, 3, 3)
    top_features = feature_importance.head(8)
    plt.barh(top_features['feature'], top_features['importance'])
    plt.title('특성 중요도 (상위 8개)')

# 4) 예측 확률 분포
plt.subplot(2, 3, 4