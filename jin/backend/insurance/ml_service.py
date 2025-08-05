"""
ML 추천 시스템 서비스
보험 상품 추천을 위한 머신러닝 서비스
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from datetime import datetime, timedelta
import json

from django.conf import settings
from django.db.models import Q, Avg, Count
from users.models import UserProfile, MLRecommendation
from .models import PolicyDocument, InsuranceCompany

# 로깅 설정
logger = logging.getLogger(__name__)


class MLRecommendationService:
    """ML 추천 시스템 서비스 클래스"""

    def __init__(self):
        """ML 추천 서비스 초기화"""
        # ML 모델 설정
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=settings.get('ML_PCA_COMPONENTS', 5))
        self.kmeans = KMeans(n_clusters=settings.get('ML_CLUSTERS', 5), random_state=42)
        self.tfidf = TfidfVectorizer(
            max_features=settings.get('ML_TFIDF_MAX_FEATURES', 1000), 
            stop_words='english'
        )
        self._initialize_models()

    def _initialize_models(self):
        """ML 모델 초기화"""
        try:
            # 사용자 데이터 로드 및 전처리
            self._load_user_data()
            self._preprocess_data()
            self._train_models()
            logger.info("ML 추천 시스템 초기화 완료")

        except Exception as e:
            logger.error(f"ML 추천 시스템 초기화 실패: {e}")
            self.user_features = None
            self.product_features = None

    def _load_user_data(self):
        """사용자 데이터 로드"""
        try:
            # 사용자 프로필 데이터 로드
            profiles = UserProfile.objects.all()

            if profiles.count() == 0:
                # 샘플 데이터 생성
                self._create_sample_data()
                profiles = UserProfile.objects.all()

            # 데이터프레임으로 변환
            user_data = []
            for profile in profiles:
                user_data.append({
                    'user_id': profile.user.id,
                    'age': profile.age or 30,
                    'gender': 1 if profile.gender == 'M' else 0,
                    'driving_experience': profile.driving_experience,
                    'annual_mileage': profile.annual_mileage,
                    'accident_history': profile.accident_history,
                    'satisfaction_score': profile.satisfaction_score or 3,
                    'selected_insurance': profile.selected_insurance or 'basic'
                })

            self.user_df = pd.DataFrame(user_data)
            logger.info(f"사용자 데이터 로드 완료: {len(user_data)}개")

        except Exception as e:
            logger.error(f"사용자 데이터 로드 실패: {e}")
            self.user_df = pd.DataFrame()

    def _create_sample_data(self):
        """샘플 데이터 생성 (개발용)"""
        from django.contrib.auth.models import User

        # 샘플 사용자 생성
        sample_users = [
            {'username': 'user1', 'age': 25, 'gender': 'M', 'driving_experience': 3, 'annual_mileage': 15000, 'accident_history': 0},
            {'username': 'user2', 'age': 35, 'gender': 'F', 'driving_experience': 8, 'annual_mileage': 8000, 'accident_history': 1},
            {'username': 'user3', 'age': 45, 'gender': 'M', 'driving_experience': 15, 'annual_mileage': 20000, 'accident_history': 2},
            {'username': 'user4', 'age': 28, 'gender': 'F', 'driving_experience': 5, 'annual_mileage': 12000, 'accident_history': 0},
            {'username': 'user5', 'age': 52, 'gender': 'M', 'driving_experience': 20, 'annual_mileage': 10000, 'accident_history': 1},
        ]

        for user_data in sample_users:
            user, created = User.objects.get_or_create(username=user_data['username'])
            if created:
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'age': user_data['age'],
                        'gender': user_data['gender'],
                        'driving_experience': user_data['driving_experience'],
                        'annual_mileage': user_data['annual_mileage'],
                        'accident_history': user_data['accident_history'],
                        'satisfaction_score': np.random.randint(3, 6),
                        'selected_insurance': np.random.choice(['basic', 'premium', 'student', 'senior'])
                    }
                )

        logger.info("샘플 데이터 생성 완료")

    def _preprocess_data(self):
        """데이터 전처리"""
        try:
            if self.user_df.empty:
                return

            # 수치형 특성 선택
            numeric_features = ['age', 'gender', 'driving_experience', 'annual_mileage', 'accident_history']

            # 특성 스케일링
            self.user_features = self.scaler.fit_transform(self.user_df[numeric_features])

            # 차원 축소
            self.user_features_pca = self.pca.fit_transform(self.user_features)

            # 클러스터링
            self.user_clusters = self.kmeans.fit_predict(self.user_features_pca)

            logger.info("데이터 전처리 완료")

        except Exception as e:
            logger.error(f"데이터 전처리 실패: {e}")

    def _train_models(self):
        """ML 모델 훈련"""
        try:
            if self.user_df.empty:
                return

            # 협업 필터링을 위한 사용자-상품 매트릭스 생성
            self._create_user_product_matrix()

            # 콘텐츠 기반 필터링을 위한 상품 특성 추출
            self._extract_product_features()

            logger.info("ML 모델 훈련 완료")

        except Exception as e:
            logger.error(f"ML 모델 훈련 실패: {e}")

    def _create_user_product_matrix(self):
        """사용자-상품 매트릭스 생성"""
        try:
            # 사용자별 선택한 보험 상품 데이터 수집
            user_product_data = []

            for profile in UserProfile.objects.all():
                if profile.selected_insurance:
                    user_product_data.append({
                        'user_id': profile.user.id,
                        'product': profile.selected_insurance,
                        'rating': profile.satisfaction_score or 3
                    })

            if user_product_data:
                self.user_product_df = pd.DataFrame(user_product_data)
                # 피벗 테이블 생성
                self.user_product_matrix = self.user_product_df.pivot_table(
                    index='user_id',
                    columns='product',
                    values='rating',
                    fill_value=0
                )
            else:
                self.user_product_matrix = pd.DataFrame()

        except Exception as e:
            logger.error(f"사용자-상품 매트릭스 생성 실패: {e}")
            self.user_product_matrix = pd.DataFrame()

    def _extract_product_features(self):
        """상품 특성 추출"""
        try:
            # 보험 상품 문서에서 특성 추출
            products = PolicyDocument.objects.all()

            product_texts = []
            for product in products:
                text = f"{product.title} {product.description or ''}"
                product_texts.append(text)

            if product_texts:
                # TF-IDF 벡터화
                self.product_features = self.tfidf.fit_transform(product_texts)
                self.product_similarity = cosine_similarity(self.product_features)
            else:
                self.product_features = None
                self.product_similarity = None

        except Exception as e:
            logger.error(f"상품 특성 추출 실패: {e}")
            self.product_features = None
            self.product_similarity = None

    def get_collaborative_recommendations(self, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """협업 필터링 기반 추천"""
        try:
            if self.user_product_matrix.empty:
                return []

            # 사용자 유사도 계산
            user_similarities = self._calculate_user_similarity(user_id)

            # 유사 사용자들의 선호 상품 기반 추천
            recommendations = []

            for similar_user_id, similarity in user_similarities[:top_k]:
                similar_user_products = self.user_product_matrix.loc[similar_user_id]
                for product, rating in similar_user_products.items():
                    if rating > 0:  # 선호하는 상품만
                        recommendations.append({
                            'product': product,
                            'score': rating * similarity,
                            'method': 'collaborative'
                        })

            # 점수별 정렬
            recommendations.sort(key=lambda x: x['score'], reverse=True)

            return recommendations[:top_k]

        except Exception as e:
            logger.error(f"협업 필터링 추천 실패: {e}")
            return []

    def get_content_based_recommendations(self, user_profile: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """콘텐츠 기반 필터링 추천"""
        try:
            if self.product_features is None:
                return []

            # 사용자 프로필을 특성 벡터로 변환
            user_features = self._extract_user_features(user_profile)

            # 상품과의 유사도 계산
            product_scores = []

            for i, product in enumerate(PolicyDocument.objects.all()):
                # 간단한 규칙 기반 점수 계산
                score = self._calculate_content_score(user_profile, product)
                product_scores.append({
                    'product_id': product.id,
                    'product_name': product.title,
                    'score': score,
                    'method': 'content_based'
                })

            # 점수별 정렬
            product_scores.sort(key=lambda x: x['score'], reverse=True)

            return product_scores[:top_k]

        except Exception as e:
            logger.error(f"콘텐츠 기반 추천 실패: {e}")
            return []

    def get_hybrid_recommendations(self, user_id: int, user_profile: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """하이브리드 추천 (협업 + 콘텐츠)"""
        try:
            # 협업 필터링 추천
            collaborative_recs = self.get_collaborative_recommendations(user_id, top_k)

            # 콘텐츠 기반 추천
            content_recs = self.get_content_based_recommendations(user_profile, top_k)

            # 하이브리드 점수 계산
            hybrid_recs = self._combine_recommendations(collaborative_recs, content_recs)

            return hybrid_recs[:top_k]

        except Exception as e:
            logger.error(f"하이브리드 추천 실패: {e}")
            return []

    def _calculate_user_similarity(self, user_id: int) -> List[Tuple[int, float]]:
        """사용자 유사도 계산"""
        try:
            if user_id not in self.user_product_matrix.index:
                return []

            # 코사인 유사도 계산
            user_vector = self.user_product_matrix.loc[user_id].values.reshape(1, -1)
            similarities = []

            for other_user_id in self.user_product_matrix.index:
                if other_user_id != user_id:
                    other_vector = self.user_product_matrix.loc[other_user_id].values.reshape(1, -1)
                    similarity = cosine_similarity(user_vector, other_vector)[0][0]
                    similarities.append((other_user_id, similarity))

            # 유사도별 정렬
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities

        except Exception as e:
            logger.error(f"사용자 유사도 계산 실패: {e}")
            return []

    def _extract_user_features(self, user_profile: Dict[str, Any]) -> np.ndarray:
        """사용자 특성 추출"""
        try:
            features = [
                user_profile.get('age', 30),
                user_profile.get('gender', 0),
                user_profile.get('driving_experience', 5),
                user_profile.get('annual_mileage', 12000),
                user_profile.get('accident_history', 0)
            ]

            return np.array(features).reshape(1, -1)

        except Exception as e:
            logger.error(f"사용자 특성 추출 실패: {e}")
            return np.array([30, 0, 5, 12000, 0]).reshape(1, -1)

    def _calculate_content_score(self, user_profile: Dict[str, Any], product: PolicyDocument) -> float:
        """콘텐츠 기반 점수 계산"""
        try:
            score = 0.0

            # 나이 기반 점수
            age = user_profile.get('age', 30)
            if age < 30:
                if 'student' in product.title.lower() or 'young' in product.title.lower():
                    score += 2.0
            elif age > 50:
                if 'senior' in product.title.lower() or 'mature' in product.title.lower():
                    score += 2.0

            # 성별 기반 점수
            gender = user_profile.get('gender', 0)
            if gender == 1:  # 남성
                if 'male' in product.title.lower():
                    score += 1.0
            else:  # 여성
                if 'female' in product.title.lower() or 'women' in product.title.lower():
                    score += 1.0

            # 운전 경력 기반 점수
            driving_exp = user_profile.get('driving_experience', 5)
            if driving_exp < 3:
                if 'new' in product.title.lower() or 'beginner' in product.title.lower():
                    score += 1.5
            elif driving_exp > 10:
                if 'experienced' in product.title.lower() or 'premium' in product.title.lower():
                    score += 1.5

            # 연간 주행거리 기반 점수
            mileage = user_profile.get('annual_mileage', 12000)
            if mileage > 15000:
                if 'high' in product.title.lower() or 'extended' in product.title.lower():
                    score += 1.0
            elif mileage < 8000:
                if 'low' in product.title.lower() or 'basic' in product.title.lower():
                    score += 1.0

            # 사고 이력 기반 점수
            accidents = user_profile.get('accident_history', 0)
            if accidents > 0:
                if 'comprehensive' in product.title.lower() or 'full' in product.title.lower():
                    score += 1.5

            return score

        except Exception as e:
            logger.error(f"콘텐츠 점수 계산 실패: {e}")
            return 0.0

    def _combine_recommendations(self, collaborative_recs: List[Dict], content_recs: List[Dict]) -> List[Dict]:
        """추천 결과 결합"""
        try:
            combined = {}

            # 협업 필터링 결과 추가
            for rec in collaborative_recs:
                product_name = rec['product']
                if product_name not in combined:
                    combined[product_name] = {
                        'product_name': product_name,
                        'collaborative_score': rec['score'],
                        'content_score': 0.0,
                        'hybrid_score': rec['score'] * 0.6  # 가중치 0.6
                    }

            # 콘텐츠 기반 결과 추가
            for rec in content_recs:
                product_name = rec['product_name']
                if product_name in combined:
                    combined[product_name]['content_score'] = rec['score']
                    combined[product_name]['hybrid_score'] += rec['score'] * 0.4  # 가중치 0.4
                else:
                    combined[product_name] = {
                        'product_name': product_name,
                        'collaborative_score': 0.0,
                        'content_score': rec['score'],
                        'hybrid_score': rec['score'] * 0.4
                    }

            # 하이브리드 점수별 정렬
            result = list(combined.values())
            result.sort(key=lambda x: x['hybrid_score'], reverse=True)

            return result

        except Exception as e:
            logger.error(f"추천 결과 결합 실패: {e}")
            return []

    def generate_recommendations(self, user_id: int, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """통합 추천 생성"""
        try:
            # 하이브리드 추천 생성
            recommendations = self.get_hybrid_recommendations(user_id, user_profile, top_k=10)

            # 유사 사용자 찾기
            similar_users = self._find_similar_users(user_id, top_k=5)

            # 추천 결과 저장
            recommendation_data = {
                'user_id': user_id,
                'recommended_products': recommendations,
                'ml_scores': {
                    'collaborative_score': sum(r.get('collaborative_score', 0) for r in recommendations),
                    'content_score': sum(r.get('content_score', 0) for r in recommendations),
                    'hybrid_score': sum(r.get('hybrid_score', 0) for r in recommendations)
                },
                'similar_users': similar_users
            }

            # 데이터베이스에 저장
            self._save_recommendation(user_id, recommendation_data)

            return recommendation_data

        except Exception as e:
            logger.error(f"추천 생성 실패: {e}")
            return {
                'user_id': user_id,
                'recommended_products': [],
                'ml_scores': {},
                'similar_users': []
            }

    def _find_similar_users(self, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """유사 사용자 찾기"""
        try:
            if self.user_df.empty:
                return []

            # 사용자 클러스터 확인
            user_idx = self.user_df[self.user_df['user_id'] == user_id].index
            if len(user_idx) == 0:
                return []

            user_cluster = self.user_clusters[user_idx[0]]

            # 같은 클러스터의 다른 사용자들
            similar_user_indices = np.where(self.user_clusters == user_cluster)[0]
            similar_users = []

            for idx in similar_user_indices[:top_k]:
                if self.user_df.iloc[idx]['user_id'] != user_id:
                    similar_users.append({
                        'user_id': int(self.user_df.iloc[idx]['user_id']),
                        'age': int(self.user_df.iloc[idx]['age']),
                        'driving_experience': int(self.user_df.iloc[idx]['driving_experience']),
                        'similarity_score': 0.8  # 클러스터 기반 유사도
                    })

            return similar_users

        except Exception as e:
            logger.error(f"유사 사용자 찾기 실패: {e}")
            return []

    def _save_recommendation(self, user_id: int, recommendation_data: Dict[str, Any]):
        """추천 결과 저장"""
        try:
            from django.contrib.auth.models import User

            user = User.objects.get(id=user_id)

            MLRecommendation.objects.create(
                user=user,
                recommended_products=recommendation_data['recommended_products'],
                ml_scores=recommendation_data['ml_scores'],
                similar_users=recommendation_data['similar_users']
            )

            logger.info(f"추천 결과 저장 완료: 사용자 {user_id}")

        except Exception as e:
            logger.error(f"추천 결과 저장 실패: {e}")

    def get_recommendation_history(self, user_id: int) -> List[Dict[str, Any]]:
        """추천 이력 조회"""
        try:
            from django.contrib.auth.models import User

            user = User.objects.get(id=user_id)
            recommendations = MLRecommendation.objects.filter(user=user).order_by('-recommendation_date')

            history = []
            for rec in recommendations:
                history.append({
                    'id': rec.id,
                    'recommendation_date': rec.recommendation_date,
                    'recommended_products_count': rec.get_recommended_products_count(),
                    'similar_users_count': rec.get_similar_users_count(),
                    'ml_scores': rec.ml_scores,
                    'user_feedback': rec.user_feedback,
                    'is_viewed': rec.is_viewed,
                    'is_selected': rec.is_selected
                })

            return history

        except Exception as e:
            logger.error(f"추천 이력 조회 실패: {e}")
            return []

    def update_user_feedback(self, recommendation_id: int, feedback: str):
        """사용자 피드백 업데이트"""
        try:
            recommendation = MLRecommendation.objects.get(id=recommendation_id)
            recommendation.user_feedback = feedback
            recommendation.save()

            logger.info(f"사용자 피드백 업데이트 완료: 추천 {recommendation_id}")

        except Exception as e:
            logger.error(f"사용자 피드백 업데이트 실패: {e}")

    def get_recommendation_stats(self) -> Dict[str, Any]:
        """추천 시스템 통계"""
        try:
            total_recommendations = MLRecommendation.objects.count()
            viewed_recommendations = MLRecommendation.objects.filter(is_viewed=True).count()
            selected_recommendations = MLRecommendation.objects.filter(is_selected=True).count()

            # 평균 만족도
            avg_satisfaction = UserProfile.objects.aggregate(
                avg_satisfaction=Avg('satisfaction_score')
            )['avg_satisfaction'] or 0

            return {
                'total_recommendations': total_recommendations,
                'viewed_recommendations': viewed_recommendations,
                'selected_recommendations': selected_recommendations,
                'view_rate': viewed_recommendations / total_recommendations if total_recommendations > 0 else 0,
                'selection_rate': selected_recommendations / total_recommendations if total_recommendations > 0 else 0,
                'avg_satisfaction': avg_satisfaction
            }

        except Exception as e:
            logger.error(f"추천 시스템 통계 조회 실패: {e}")
            return {}
