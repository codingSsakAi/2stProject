import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class InsurancePremiumPredictor:
    """
    보험료 예측을 위한 머신러닝 모델 클래스
    """

    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = [
            "age",
            "gender",
            "driving_experience",
            "annual_mileage",
            "accident_history",
            "residence_area",
            "car_type",
            "coverage_level",
        ]
        self.model_path = "chatbot/models/insurance_premium_predictor.pkl"
        self.encoders_path = "chatbot/models/label_encoders.pkl"
        self.scaler_path = "chatbot/models/scaler.pkl"

        # 모델 디렉토리 생성
        os.makedirs("chatbot/models", exist_ok=True)

        # 모델 로드 시도
        self.load_model()

    def generate_mock_training_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """
        모의 훈련 데이터 생성
        """
        np.random.seed(42)

        data = {
            "age": np.random.randint(18, 80, n_samples),
            "gender": np.random.choice(["M", "F"], n_samples),
            "driving_experience": np.random.randint(0, 50, n_samples),
            "annual_mileage": np.random.randint(1000, 50000, n_samples),
            "accident_history": np.random.randint(0, 10, n_samples),
            "residence_area": np.random.choice(
                [
                    "서울",
                    "부산",
                    "대구",
                    "인천",
                    "광주",
                    "대전",
                    "울산",
                    "세종",
                    "기타",
                ],
                n_samples,
            ),
            "car_type": np.random.choice(
                ["경차", "소형", "준중형", "중형", "대형", "SUV"], n_samples
            ),
            "coverage_level": np.random.choice(
                ["기본", "표준", "고급", "프리미엄"], n_samples
            ),
        }

        df = pd.DataFrame(data)

        # 보험료 계산 (실제 보험료 계산 로직과 유사하게)
        df["premium"] = self._calculate_mock_premium(df)

        return df

    def _calculate_mock_premium(self, df: pd.DataFrame) -> np.ndarray:
        """
        실제 보험료 계산 로직과 일치하는 모의 보험료 계산
        """
        # 실제 보험사들의 평균 기본 요율 사용
        base_premium = 800000  # 실제 보험사들의 평균 기본 요율

        # 나이별 요율 (실제 로직과 일치)
        age_factor = np.where(
            df["age"] < 25,
            1.3,
            np.where(df["age"] < 40, 1.0, np.where(df["age"] < 60, 0.87, 1.1)),
        )

        # 성별 요율 (실제 로직과 일치)
        gender_factor = np.where(df["gender"] == "M", 1.0, 0.93)

        # 운전 경력 할인 (실제 로직과 일치)
        experience_discount = np.minimum(df["driving_experience"] * 0.04, 0.5)
        experience_factor = 1.0 - experience_discount

        # 연간 주행거리 요율 (실제 로직과 일치)
        mileage_factor = np.where(
            df["annual_mileage"] < 5000,
            0.85,
            np.where(df["annual_mileage"] < 20000, 1.0, 1.15),
        )

        # 사고 경력 할증 (실제 로직과 일치)
        accident_penalty = df["accident_history"] * 0.25
        accident_factor = 1.0 + accident_penalty

        # 거주 지역 요율 (실제 로직과 일치)
        area_factors = {
            "서울": 1.1,
            "부산": 0.96,
            "대구": 0.91,
            "인천": 1.05,
            "광주": 0.93,
            "대전": 0.93,
            "울산": 0.95,
            "세종": 0.88,
            "기타": 0.89,
        }
        area_factor = df["residence_area"].map(area_factors)

        # 차종 요율 (실제 로직과 일치)
        car_factors = {
            "경차": 0.8,
            "소형": 0.9,
            "준중형": 1.0,
            "중형": 1.14,
            "대형": 1.3,
            "SUV": 1.19,
        }
        car_factor = df["car_type"].map(car_factors)

        # 보장 수준 요율 (실제 로직과 일치)
        coverage_factors = {"기본": 0.8, "표준": 1.0, "고급": 1.3, "프리미엄": 1.6}
        coverage_factor = df["coverage_level"].map(coverage_factors)

        # 최종 보험료 계산 (실제 로직과 일치)
        premium = (
            base_premium
            * age_factor
            * gender_factor
            * experience_factor
            * mileage_factor
            * accident_factor
            * area_factor
            * car_factor
            * coverage_factor
        )

        # 랜덤 변동 요소 추가 (±5%, 실제 로직과 일치)
        random_factor = np.random.uniform(0.95, 1.05, len(premium))
        premium = premium * random_factor

        # 특별 할인 적용 (10% 확률로 10% 할인)
        special_discount = np.random.choice([0.9, 1.0], size=len(premium), p=[0.1, 0.9])
        premium = premium * special_discount

        return np.round(premium, -3)  # 1000원 단위로 반올림

    def preprocess_data(self, df: pd.DataFrame, for_prediction: bool = False) -> tuple:
        """
        데이터 전처리
        """
        # 범주형 변수 인코딩
        categorical_features = [
            "gender",
            "residence_area",
            "car_type",
            "coverage_level",
        ]

        for feature in categorical_features:
            if feature not in self.label_encoders:
                self.label_encoders[feature] = LabelEncoder()
                df[f"{feature}_encoded"] = self.label_encoders[feature].fit_transform(
                    df[feature]
                )
            else:
                df[f"{feature}_encoded"] = self.label_encoders[feature].transform(
                    df[feature]
                )

        # 특성 선택
        feature_columns = [
            "age",
            "driving_experience",
            "annual_mileage",
            "accident_history",
        ] + [f"{f}_encoded" for f in categorical_features]

        X = df[feature_columns]

        if for_prediction:
            # 예측 시에는 y 값이 없음
            X_scaled = self.scaler.transform(X)
            return X_scaled, None, feature_columns
        else:
            # 훈련 시에는 y 값이 있음
            y = df["premium"]
            X_scaled = self.scaler.fit_transform(X)
            return X_scaled, y, feature_columns

    def train_model(self, df: pd.DataFrame = None) -> Dict[str, float]:
        """
        모델 훈련
        """
        if df is None:
            df = self.generate_mock_training_data(2000)

        logger.info(f"훈련 데이터 크기: {len(df)}")

        # 데이터 전처리
        X, y, feature_columns = self.preprocess_data(df)

        # 훈련/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # 모델 초기화 및 훈련
        self.model = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        )

        logger.info("모델 훈련 시작...")
        self.model.fit(X_train, y_train)

        # 예측 및 평가
        y_pred = self.model.predict(X_test)

        metrics = {
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred),
            "mape": np.mean(np.abs((y_test - y_pred) / y_test)) * 100,
        }

        logger.info(
            f"모델 성능: MAE={metrics['mae']:.0f}, RMSE={metrics['rmse']:.0f}, R²={metrics['r2']:.3f}, MAPE={metrics['mape']:.1f}%"
        )

        # 모델 저장
        self.save_model()

        return metrics

    def predict_premium(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 프로필을 기반으로 보험료 예측
        """
        try:
            if self.model is None:
                logger.warning("모델이 로드되지 않았습니다. 기본값을 반환합니다.")
                return {
                    "predicted_premium": 500000,
                    "confidence_score": 0.5,
                    "prediction_timestamp": datetime.now().isoformat(),
                    "model_version": "1.0",
                }

            # 사용자 데이터를 DataFrame으로 변환
            user_data = pd.DataFrame(
                [
                    {
                        "age": user_profile.get("age", 30),
                        "gender": user_profile.get("gender", "M"),
                        "driving_experience": user_profile.get("driving_experience", 5),
                        "annual_mileage": user_profile.get("annual_mileage", 12000),
                        "accident_history": user_profile.get("accident_history", 0),
                        "residence_area": user_profile.get("residence_area", "서울"),
                        "car_type": user_profile.get("car_type", "준중형"),
                        "coverage_level": user_profile.get("coverage_level", "표준"),
                    }
                ]
            )

            # 전처리 (예측용)
            X, _, feature_columns = self.preprocess_data(user_data, for_prediction=True)

            # 예측
            predicted_premium = self.model.predict(X)[0]

            # 신뢰도 점수 계산 (모델의 예측 확률 기반)
            confidence_score = self._calculate_confidence_score(X[0])

            return {
                "predicted_premium": int(predicted_premium),
                "confidence_score": confidence_score,
                "prediction_timestamp": datetime.now().isoformat(),
                "model_version": "1.0",
            }

        except Exception as e:
            logger.error(f"보험료 예측 중 오류: {e}", exc_info=True)
            return {
                "predicted_premium": 500000,
                "confidence_score": 0.5,
                "prediction_timestamp": datetime.now().isoformat(),
                "model_version": "1.0",
                "error": str(e),
            }

    def _calculate_confidence_score(self, features: np.ndarray) -> float:
        """
        예측 신뢰도 점수 계산
        """
        # Random Forest의 예측 분산을 기반으로 신뢰도 계산
        predictions = []
        for estimator in self.model.estimators_:
            predictions.append(estimator.predict([features])[0])

        # 예측 분산이 작을수록 신뢰도가 높음
        variance = np.var(predictions)
        mean_pred = np.mean(predictions)

        # 정규화된 신뢰도 점수 (0-1)
        confidence = max(0, 1 - (variance / (mean_pred**2)))

        return min(1.0, confidence)

    def save_model(self):
        """
        모델 저장
        """
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.label_encoders, self.encoders_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("모델이 성공적으로 저장되었습니다.")
        except Exception as e:
            logger.error(f"모델 저장 중 오류: {e}")

    def load_model(self):
        """
        모델 로드
        """
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.label_encoders = joblib.load(self.encoders_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("모델이 성공적으로 로드되었습니다.")
                return True
        except Exception as e:
            logger.error(f"모델 로드 중 오류: {e}")

        return False

    def get_feature_importance(self) -> Dict[str, float]:
        """
        특성 중요도 반환
        """
        if self.model is None:
            return {}

        feature_names = [
            "나이",
            "운전경력",
            "연간주행거리",
            "사고경력",
            "성별",
            "거주지역",
            "차종",
            "보장수준",
        ]

        importance = self.model.feature_importances_

        return dict(zip(feature_names, importance))


class CustomerBehaviorAnalyzer:
    """
    고객 행동 분석을 위한 클래스
    """

    def __init__(self):
        self.interaction_data = []

    def record_interaction(self, user_id: int, action: str, data: Dict[str, Any]):
        """
        사용자 상호작용 기록
        """
        interaction = {
            "user_id": user_id,
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self.interaction_data.append(interaction)

    def analyze_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        사용자 선호도 분석
        """
        user_interactions = [
            i for i in self.interaction_data if i["user_id"] == user_id
        ]

        if not user_interactions:
            return {"preferences": {}, "confidence": 0.0}

        # 행동 패턴 분석
        preferences = {
            "preferred_coverage_level": self._analyze_coverage_preference(
                user_interactions
            ),
            "preferred_car_type": self._analyze_car_preference(user_interactions),
            "price_sensitivity": self._analyze_price_sensitivity(user_interactions),
            "interaction_frequency": len(user_interactions),
        }

        confidence = min(
            1.0, len(user_interactions) / 10
        )  # 상호작용이 많을수록 신뢰도 높음

        return {"preferences": preferences, "confidence": confidence}

    def _analyze_coverage_preference(self, interactions: List[Dict]) -> str:
        """보장 수준 선호도 분석"""
        coverage_counts = {}
        for interaction in interactions:
            if interaction["action"] == "view_coverage":
                coverage = interaction["data"].get("coverage_level", "표준")
                coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1

        if coverage_counts:
            return max(coverage_counts, key=coverage_counts.get)
        return "표준"

    def _analyze_car_preference(self, interactions: List[Dict]) -> str:
        """차종 선호도 분석"""
        car_counts = {}
        for interaction in interactions:
            if interaction["action"] == "view_car_type":
                car_type = interaction["data"].get("car_type", "준중형")
                car_counts[car_type] = car_counts.get(car_type, 0) + 1

        if car_counts:
            return max(car_counts, key=car_counts.get)
        return "준중형"

    def _analyze_price_sensitivity(self, interactions: List[Dict]) -> str:
        """가격 민감도 분석"""
        price_related_actions = 0
        total_actions = len(interactions)

        for interaction in interactions:
            if interaction["action"] in ["view_lowest_price", "compare_prices"]:
                price_related_actions += 1

        sensitivity_ratio = (
            price_related_actions / total_actions if total_actions > 0 else 0
        )

        if sensitivity_ratio > 0.7:
            return "높음"
        elif sensitivity_ratio > 0.3:
            return "보통"
        else:
            return "낮음"
