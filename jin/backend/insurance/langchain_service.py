"""
LangChain + LLM 통합 서비스
보험 추천 시스템을 위한 LangChain 기반 LLM 서비스
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_upstage import UpstageEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from django.conf import settings

from .models import PolicyDocument, InsuranceCompany
from .services import RAGService
from .ml_service import MLRecommendationService

# 로깅 설정
logger = logging.getLogger(__name__)


class LangChainService:
    """LangChain 기반 LLM 서비스 클래스"""

    def __init__(self):
        """LangChain 서비스 초기화"""
        self._initialize_llm()
        self._initialize_memory()
        self._initialize_tools()
        self._initialize_agent()
        self.rag_service = RAGService()
        self.ml_service = MLRecommendationService()

    def _initialize_llm(self):
        """LLM 초기화"""
        try:
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API 키가 설정되지 않았습니다.")
                self.llm = None
                return

            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                api_key=settings.OPENAI_API_KEY
            )
            logger.info("LangChain LLM 초기화 완료")

        except Exception as e:
            logger.error(f"LangChain LLM 초기화 실패: {e}")
            self.llm = None

    def _initialize_memory(self):
        """대화 메모리 초기화"""
        try:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            logger.info("대화 메모리 초기화 완료")

        except Exception as e:
            logger.error(f"대화 메모리 초기화 실패: {e}")
            self.memory = None

    def _initialize_tools(self):
        """도구(Tools) 초기화"""
        try:
            self.tools = [
                Tool(
                    name="보험_문서_검색",
                    description="보험 약관 문서를 검색하여 관련 정보를 찾습니다.",
                    func=self._search_insurance_documents
                ),
                Tool(
                    name="보험_회사_정보_조회",
                    description="보험 회사의 상세 정보를 조회합니다.",
                    func=self._get_insurance_company_info
                ),
                Tool(
                    name="보험_추천_생성",
                    description="사용자 정보를 바탕으로 맞춤형 보험을 추천합니다.",
                    func=self._generate_insurance_recommendation
                ),
                Tool(
                    name="보험_비교_분석",
                    description="여러 보험 상품을 비교 분석합니다.",
                    func=self._compare_insurance_products
                ),
                Tool(
                    name="ML_추천_시스템",
                    description="머신러닝 기반 보험 상품 추천 시스템을 사용합니다.",
                    func=self._ml_recommendation_system
                ),
                Tool(
                    name="사용자_프로필_분석",
                    description="사용자 프로필을 분석하여 맞춤형 추천을 생성합니다.",
                    func=self._analyze_user_profile
                )
            ]
            logger.info("도구(Tools) 초기화 완료")

        except Exception as e:
            logger.error(f"도구(Tools) 초기화 실패: {e}")
            self.tools = []

    def _initialize_agent(self):
        """에이전트 초기화"""
        try:
            if not self.llm or not self.tools:
                logger.warning("LLM 또는 도구가 초기화되지 않아 에이전트를 생성할 수 없습니다.")
                self.agent = None
                return

            self.agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True
            )
            logger.info("LangChain 에이전트 초기화 완료")

        except Exception as e:
            logger.error(f"LangChain 에이전트 초기화 실패: {e}")
            self.agent = None

    def _search_insurance_documents(self, query: str) -> str:
        """보험 문서 검색 도구"""
        try:
            if not self.rag_service:
                return "RAG 서비스가 초기화되지 않았습니다."

            results = self.rag_service.search_documents(query, top_k=5)
            
            if not results:
                return "관련된 보험 문서를 찾을 수 없습니다."

            response = "검색 결과:\n\n"
            for i, result in enumerate(results, 1):
                response += f"{i}. {result.get('title', '제목 없음')}\n"
                response += f"   내용: {result.get('content', '내용 없음')[:200]}...\n"
                response += f"   유사도: {result.get('score', 0):.3f}\n\n"

            return response

        except Exception as e:
            logger.error(f"보험 문서 검색 실패: {e}")
            return f"검색 중 오류가 발생했습니다: {str(e)}"

    def _get_insurance_company_info(self, company_name: str) -> str:
        """보험 회사 정보 조회 도구"""
        try:
            company = InsuranceCompany.objects.filter(
                name__icontains=company_name
            ).first()

            if not company:
                return f"'{company_name}' 회사를 찾을 수 없습니다."

            response = f"보험 회사 정보:\n\n"
            response += f"회사명: {company.name}\n"
            response += f"설립일: {company.established_date}\n"
            response += f"주소: {company.address}\n"
            response += f"전화번호: {company.phone}\n"
            response += f"웹사이트: {company.website}\n"
            response += f"설명: {company.description}\n"

            return response

        except Exception as e:
            logger.error(f"보험 회사 정보 조회 실패: {e}")
            return f"회사 정보 조회 중 오류가 발생했습니다: {str(e)}"

    def _generate_insurance_recommendation(self, user_info: str) -> str:
        """보험 추천 생성 도구"""
        try:
            # 사용자 정보 파싱 (간단한 예시)
            user_profile = self._parse_user_info(user_info)
            
            # 추천 로직 구현
            recommendation = self._create_recommendation(user_profile)
            
            return recommendation

        except Exception as e:
            logger.error(f"보험 추천 생성 실패: {e}")
            return f"추천 생성 중 오류가 발생했습니다: {str(e)}"

    def _compare_insurance_products(self, product_names: str) -> str:
        """보험 상품 비교 분석 도구"""
        try:
            products = product_names.split(',')
            comparison_result = "보험 상품 비교 분석:\n\n"

            for product_name in products:
                product_name = product_name.strip()
                documents = PolicyDocument.objects.filter(
                    title__icontains=product_name
                )[:3]

                if documents:
                    comparison_result += f"📋 {product_name}:\n"
                    for doc in documents:
                        comparison_result += f"  - {doc.title}\n"
                        comparison_result += f"    업로드일: {doc.upload_date}\n"
                        comparison_result += f"    파일크기: {doc.file_size} bytes\n\n"
                else:
                    comparison_result += f"❌ {product_name}: 관련 문서 없음\n\n"

            return comparison_result

        except Exception as e:
            logger.error(f"보험 상품 비교 분석 실패: {e}")
            return f"비교 분석 중 오류가 발생했습니다: {str(e)}"

    def _ml_recommendation_system(self, user_input: str) -> str:
        """ML 추천 시스템 도구"""
        try:
            # 사용자 정보 파싱
            user_profile = self._parse_user_info(user_input)
            
            # 샘플 사용자 ID (실제로는 인증된 사용자 ID 사용)
            sample_user_id = 1
            
            # ML 추천 생성
            recommendations = self.ml_service.generate_recommendations(sample_user_id, user_profile)
            
            if not recommendations.get('recommended_products'):
                return "ML 추천 시스템에서 추천할 상품을 찾을 수 없습니다."
            
            response = "🤖 ML 추천 시스템 결과:\n\n"
            response += f"📊 ML 점수:\n"
            response += f"  - 협업 필터링: {recommendations['ml_scores'].get('collaborative_score', 0):.2f}\n"
            response += f"  - 콘텐츠 기반: {recommendations['ml_scores'].get('content_score', 0):.2f}\n"
            response += f"  - 하이브리드: {recommendations['ml_scores'].get('hybrid_score', 0):.2f}\n\n"
            
            response += "🎯 추천 상품:\n"
            for i, product in enumerate(recommendations['recommended_products'][:5], 1):
                response += f"{i}. {product.get('product_name', '알 수 없는 상품')}\n"
                response += f"   하이브리드 점수: {product.get('hybrid_score', 0):.2f}\n"
                response += f"   협업 필터링: {product.get('collaborative_score', 0):.2f}\n"
                response += f"   콘텐츠 기반: {product.get('content_score', 0):.2f}\n\n"
            
            if recommendations.get('similar_users'):
                response += "👥 유사 사용자:\n"
                for i, similar_user in enumerate(recommendations['similar_users'][:3], 1):
                    response += f"{i}. 사용자 ID: {similar_user.get('user_id')}\n"
                    response += f"   나이: {similar_user.get('age')}세\n"
                    response += f"   운전 경력: {similar_user.get('driving_experience')}년\n"
                    response += f"   유사도: {similar_user.get('similarity_score', 0):.2f}\n\n"
            
            return response

        except Exception as e:
            logger.error(f"ML 추천 시스템 실패: {e}")
            return f"ML 추천 시스템 오류: {str(e)}"

    def _analyze_user_profile(self, user_info: str) -> str:
        """사용자 프로필 분석 도구"""
        try:
            # 사용자 정보 파싱
            user_profile = self._parse_user_info(user_info)
            
            response = "📊 사용자 프로필 분석:\n\n"
            response += f"나이: {user_profile.get('age', '알 수 없음')}세\n"
            response += f"성별: {user_profile.get('gender', '알 수 없음')}\n"
            response += f"운전 경력: {user_profile.get('driving_experience', '알 수 없음')}년\n"
            response += f"연간 주행거리: {user_profile.get('annual_mileage', '알 수 없음')}km\n"
            response += f"사고 이력: {user_profile.get('accident_history', '알 수 없음')}회\n\n"
            
            # 프로필 기반 분석
            analysis = self._analyze_profile_characteristics(user_profile)
            response += "🎯 프로필 특성 분석:\n"
            response += analysis
            
            return response

        except Exception as e:
            logger.error(f"사용자 프로필 분석 실패: {e}")
            return f"프로필 분석 중 오류가 발생했습니다: {str(e)}"

    def _analyze_profile_characteristics(self, user_profile: Dict[str, Any]) -> str:
        """프로필 특성 분석"""
        analysis = ""
        
        age = user_profile.get('age', 30)
        gender = user_profile.get('gender', '알 수 없음')
        driving_exp = user_profile.get('driving_experience', 5)
        mileage = user_profile.get('annual_mileage', 12000)
        accidents = user_profile.get('accident_history', 0)
        
        # 나이 분석
        if age < 25:
            analysis += "• 젊은 운전자 (25세 미만)\n"
            analysis += "  - 학생 할인 혜택 가능\n"
            analysis += "  - 초보 운전자 특별 보장\n"
        elif age < 40:
            analysis += "• 중년 운전자 (25-40세)\n"
            analysis += "  - 안정적인 보험료\n"
            analysis += "  - 다양한 보장 옵션\n"
        else:
            analysis += "• 성숙한 운전자 (40세 이상)\n"
            analysis += "  - 경험자 할인 혜택\n"
            analysis += "  - 종합 보장 추천\n"
        
        # 운전 경력 분석
        if driving_exp < 3:
            analysis += "• 초보 운전자\n"
            analysis += "  - 기본 보장 강화\n"
            analysis += "  - 사고 시 특별 보장\n"
        elif driving_exp < 10:
            analysis += "• 중급 운전자\n"
            analysis += "  - 균형잡힌 보장\n"
            analysis += "  - 합리적인 보험료\n"
        else:
            analysis += "• 숙련된 운전자\n"
            analysis += "  - 할인 혜택 적용\n"
            analysis += "  - 선택적 보장\n"
        
        # 주행거리 분석
        if mileage < 8000:
            analysis += "• 저주행 운전자\n"
            analysis += "  - 저렴한 보험료\n"
            analysis += "  - 기본 보장\n"
        elif mileage < 15000:
            analysis += "• 일반 주행 운전자\n"
            analysis += "  - 표준 보장\n"
            analysis += "  - 적정 보험료\n"
        else:
            analysis += "• 고주행 운전자\n"
            analysis += "  - 확장 보장\n"
            analysis += "  - 사고 위험 고려\n"
        
        # 사고 이력 분석
        if accidents == 0:
            analysis += "• 무사고 운전자\n"
            analysis += "  - 할인 혜택 적용\n"
            analysis += "  - 우량 운전자 보장\n"
        elif accidents == 1:
            analysis += "• 경미한 사고 이력\n"
            analysis += "  - 기본 보장 유지\n"
            analysis += "  - 보험료 조정 필요\n"
        else:
            analysis += "• 다중 사고 이력\n"
            analysis += "  - 종합 보장 필요\n"
            analysis += "  - 높은 보험료\n"
        
        return analysis

    def _parse_user_info(self, user_info: str) -> Dict[str, Any]:
        """사용자 정보 파싱"""
        profile = {
            "age": None,
            "gender": None,
            "occupation": None,
            "income_level": None,
            "family_status": None,
            "health_condition": None,
            "driving_experience": None,
            "annual_mileage": None,
            "accident_history": None
        }

        # 간단한 키워드 기반 파싱
        user_info_lower = user_info.lower()
        
        if "남성" in user_info_lower or "남자" in user_info_lower:
            profile["gender"] = "남성"
        elif "여성" in user_info_lower or "여자" in user_info_lower:
            profile["gender"] = "여성"

        if "학생" in user_info_lower:
            profile["occupation"] = "학생"
        elif "회사원" in user_info_lower or "직장인" in user_info_lower:
            profile["occupation"] = "회사원"
        elif "자영업" in user_info_lower:
            profile["occupation"] = "자영업자"

        if "고소득" in user_info_lower or "높은 수입" in user_info_lower:
            profile["income_level"] = "고소득"
        elif "중간" in user_info_lower:
            profile["income_level"] = "중간소득"
        elif "저소득" in user_info_lower:
            profile["income_level"] = "저소득"

        # 나이 파싱
        import re
        age_match = re.search(r'(\d+)세', user_info)
        if age_match:
            profile["age"] = int(age_match.group(1))

        # 운전 경력 파싱
        exp_match = re.search(r'(\d+)년', user_info)
        if exp_match:
            profile["driving_experience"] = int(exp_match.group(1))

        # 주행거리 파싱
        mileage_match = re.search(r'(\d+)km', user_info)
        if mileage_match:
            profile["annual_mileage"] = int(mileage_match.group(1))

        # 사고 이력 파싱
        accident_match = re.search(r'사고.*?(\d+)', user_info)
        if accident_match:
            profile["accident_history"] = int(accident_match.group(1))

        return profile

    def _create_recommendation(self, user_profile: Dict[str, Any]) -> str:
        """사용자 프로필 기반 추천 생성"""
        recommendation = "🎯 맞춤형 보험 추천:\n\n"
        
        # 기본 추천 로직
        recommendations = []
        
        if user_profile["occupation"] == "학생":
            recommendations.append("📚 학생 전용 자동차보험 (할인 혜택)")
        
        if user_profile["income_level"] == "고소득":
            recommendations.append("💎 프리미엄 자동차보험 (높은 보장)")
        elif user_profile["income_level"] == "저소득":
            recommendations.append("💰 경제형 자동차보험 (저렴한 보험료)")
        
        if user_profile["gender"] == "여성":
            recommendations.append("👩 여성 전용 자동차보험 (특별 혜택)")
        
        # 나이 기반 추천
        age = user_profile.get("age", 30)
        if age < 25:
            recommendations.append("🚗 초보 운전자 보험 (사고 시 특별 보장)")
        elif age > 50:
            recommendations.append("👴 시니어 운전자 보험 (경험자 할인)")
        
        # 운전 경력 기반 추천
        driving_exp = user_profile.get("driving_experience", 5)
        if driving_exp < 3:
            recommendations.append("🆕 신규 운전자 보험 (기본 보장 강화)")
        elif driving_exp > 10:
            recommendations.append("🏆 숙련 운전자 보험 (할인 혜택)")
        
        # 기본 추천
        recommendations.append("🚗 기본 자동차보험 (필수 보장)")
        
        for i, rec in enumerate(recommendations, 1):
            recommendation += f"{i}. {rec}\n"
        
        recommendation += "\n💡 추천 이유:\n"
        recommendation += "- 사용자 프로필을 기반으로 한 맞춤형 추천\n"
        recommendation += "- 보장 범위와 보험료를 고려한 최적화\n"
        recommendation += "- 특별 할인 및 혜택 적용 가능\n"
        
        return recommendation

    def chat_with_agent(self, user_message: str) -> str:
        """에이전트와 대화"""
        try:
            if not self.agent:
                return "에이전트가 초기화되지 않았습니다."

            # 시스템 메시지 추가
            system_message = """당신은 자동차 보험 전문 상담사입니다. 
            사용자의 질문에 대해 친절하고 전문적으로 답변해주세요.
            보험 관련 정보를 제공할 때는 정확하고 이해하기 쉽게 설명해주세요.
            ML 추천 시스템과 RAG 시스템을 활용하여 정확한 정보를 제공하세요."""

            # 에이전트 실행
            response = self.agent.run(
                f"{system_message}\n\n사용자: {user_message}"
            )

            return response

        except Exception as e:
            logger.error(f"에이전트 대화 실패: {e}")
            return f"대화 중 오류가 발생했습니다: {str(e)}"

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 기록 조회"""
        try:
            if not self.memory:
                return []

            history = []
            chat_history = self.memory.chat_memory.messages

            for i in range(0, len(chat_history), 2):
                if i + 1 < len(chat_history):
                    history.append({
                        "user": chat_history[i].content,
                        "assistant": chat_history[i + 1].content
                    })

            return history

        except Exception as e:
            logger.error(f"대화 기록 조회 실패: {e}")
            return []

    def clear_memory(self):
        """대화 메모리 초기화"""
        try:
            if self.memory:
                self.memory.clear()
                logger.info("대화 메모리 초기화 완료")
        except Exception as e:
            logger.error(f"대화 메모리 초기화 실패: {e}")

    def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 조회"""
        return {
            "llm_initialized": self.llm is not None,
            "memory_initialized": self.memory is not None,
            "tools_count": len(self.tools),
            "agent_initialized": self.agent is not None,
            "rag_service_available": self.rag_service is not None,
            "ml_service_available": self.ml_service is not None
        } 