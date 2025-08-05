"""
LangChain + LLM 서비스
LangChain을 사용한 대화형 AI 서비스
"""

import logging
import re
from typing import List, Dict, Any, Optional
from django.conf import settings

from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain.schema import SystemMessage

from .services import RAGService
from .ml_service import MLRecommendationService

# 로깅 설정
logger = logging.getLogger(__name__)


class LangChainService:
    """LangChain 기반 AI 서비스 클래스"""

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
            api_key = settings.OPENAI_API_KEY
            model_name = settings.OPENAI_MODEL
            max_tokens = settings.OPENAI_MAX_TOKENS
            temperature = settings.OPENAI_TEMPERATURE

            if not api_key:
                logger.warning("OpenAI API 키가 설정되지 않았습니다.")
                self.llm = None
                return

            self.llm = ChatOpenAI(
                openai_api_key=api_key,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            logger.info("LLM 초기화 완료")

        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}")
            self.llm = None

    def _initialize_memory(self):
        """대화 메모리 초기화"""
        try:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True
            )
            logger.info("대화 메모리 초기화 완료")

        except Exception as e:
            logger.error(f"대화 메모리 초기화 실패: {e}")
            self.memory = None

    def _initialize_tools(self):
        """도구 초기화"""
        try:
            self.tools = [
                Tool(
                    name="보험_문서_검색",
                    func=self._search_insurance_documents,
                    description="보험 관련 문서를 검색합니다. 검색어를 입력하세요.",
                ),
                Tool(
                    name="보험사_정보",
                    func=self._get_insurance_company_info,
                    description="보험사 정보를 조회합니다. 보험사 이름을 입력하세요.",
                ),
                Tool(
                    name="보험_추천",
                    func=self._generate_insurance_recommendation,
                    description="사용자 정보를 바탕으로 보험을 추천합니다. 나이, 성별, 운전경력 등을 포함한 사용자 정보를 입력하세요.",
                ),
                Tool(
                    name="보험_상품_비교",
                    func=self._compare_insurance_products,
                    description="보험 상품들을 비교합니다. 비교할 상품명들을 쉼표로 구분하여 입력하세요.",
                ),
                Tool(
                    name="ML_추천_시스템",
                    func=self._ml_recommendation_system,
                    description="머신러닝 기반 보험 추천 시스템입니다. 사용자 ID와 프로필 정보(나이, 성별, 운전경력, 연간주행거리, 사고이력)를 입력하세요.",
                ),
                Tool(
                    name="사용자_프로필_분석",
                    func=self._analyze_user_profile,
                    description="사용자 프로필을 분석하여 특성을 파악합니다. 사용자 정보(나이, 성별, 운전경력, 연간주행거리, 사고이력)를 입력하세요.",
                ),
            ]
            logger.info("도구 초기화 완료")

        except Exception as e:
            logger.error(f"도구 초기화 실패: {e}")
            self.tools = []

    def _initialize_agent(self):
        """에이전트 초기화"""
        try:
            if self.llm is None:
                logger.warning("LLM이 초기화되지 않아 에이전트를 생성할 수 없습니다.")
                self.agent = None
                return

            system_message = SystemMessage(
                content="""
            당신은 자동차 보험 전문 상담사입니다. 
            사용자의 질문에 대해 정확하고 도움이 되는 답변을 제공하세요.
            RAG 시스템과 ML 추천 시스템을 활용하여 최적의 답변을 제공합니다.
            답변은 친근하고 이해하기 쉽게 작성하되, 전문성을 유지하세요.
            """
            )

            self.agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True,
                agent_kwargs={"system_message": system_message},
            )
            logger.info("에이전트 초기화 완료")

        except Exception as e:
            logger.error(f"에이전트 초기화 실패: {e}")
            self.agent = None

    def _search_insurance_documents(self, query: str) -> str:
        """보험 문서 검색"""
        try:
            if self.rag_service is None:
                return "RAG 서비스가 초기화되지 않았습니다."

            results = self.rag_service.search_documents(query, top_k=3)

            if not results:
                return "관련 문서를 찾을 수 없습니다."

            response = "검색 결과:\n\n"
            for i, result in enumerate(results, 1):
                response += f"{i}. {result['content'][:200]}...\n\n"

            return response

        except Exception as e:
            logger.error(f"보험 문서 검색 실패: {e}")
            return f"검색 중 오류가 발생했습니다: {str(e)}"

    def _get_insurance_company_info(self, company_name: str) -> str:
        """보험사 정보 조회"""
        try:
            # 실제 구현에서는 데이터베이스에서 보험사 정보를 조회
            company_info = {
                "삼성화재": "대한민국 최대 보험사 중 하나로, 자동차보험 시장에서 높은 점유율을 보유하고 있습니다.",
                "현대해상": "현대자동차그룹 계열사로, 자동차 전문 보험사로서 차별화된 서비스를 제공합니다.",
                "KB손보": "KB금융그룹 계열사로, 안정적인 재무구조와 다양한 보험상품을 제공합니다.",
                "롯데손보": "롯데그룹 계열사로, 고객 중심의 서비스와 혁신적인 보험상품을 제공합니다.",
                "메리츠화재": "메리츠금융그룹 계열사로, 디지털 혁신과 고객 편의성을 중시합니다.",
            }

            if company_name in company_info:
                return f"{company_name} 정보:\n{company_info[company_name]}"
            else:
                return f"{company_name}에 대한 정보를 찾을 수 없습니다."

        except Exception as e:
            logger.error(f"보험사 정보 조회 실패: {e}")
            return f"정보 조회 중 오류가 발생했습니다: {str(e)}"

    def _generate_insurance_recommendation(self, user_info: str) -> str:
        """보험 추천 생성"""
        try:
            # 사용자 정보 파싱
            parsed_info = self._parse_user_info(user_info)

            if not parsed_info:
                return "사용자 정보를 파싱할 수 없습니다. 나이, 성별, 운전경력 등을 포함하여 입력해주세요."

            # 기본 추천 로직
            age = parsed_info.get("age", 30)
            gender = parsed_info.get("gender", "M")
            driving_experience = parsed_info.get("driving_experience", 5)

            recommendations = []

            # 나이 기반 추천
            if age < 30:
                recommendations.append(
                    "신규 운전자 특별보험 - 저렴한 보험료와 기본 보장"
                )
            elif age > 50:
                recommendations.append("시니어 특별보험 - 안전 운전 할인과 추가 보장")

            # 운전 경력 기반 추천
            if driving_experience < 3:
                recommendations.append("초보 운전자 보험 - 사고 위험 대비 특별 보장")
            elif driving_experience > 10:
                recommendations.append(
                    "베테랑 운전자 보험 - 안전 운전 할인과 프리미엄 서비스"
                )

            # 성별 기반 추천
            if gender == "F":
                recommendations.append("여성 운전자 특별보험 - 여성 특화 서비스와 할인")

            response = (
                f"사용자 정보: {age}세, {gender}, 운전경력 {driving_experience}년\n\n"
            )
            response += "추천 보험상품:\n"
            for i, rec in enumerate(recommendations, 1):
                response += f"{i}. {rec}\n"

            return response

        except Exception as e:
            logger.error(f"보험 추천 생성 실패: {e}")
            return f"추천 생성 중 오류가 발생했습니다: {str(e)}"

    def _compare_insurance_products(self, product_names: str) -> str:
        """보험 상품 비교"""
        try:
            products = [name.strip() for name in product_names.split(",")]

            if len(products) < 2:
                return "비교할 상품을 2개 이상 입력해주세요."

            # 실제 구현에서는 데이터베이스에서 상품 정보를 조회
            comparison_data = {
                "기본 자동차보험": {
                    "보장범위": "기본적인 사고 보장",
                    "보험료": "저렴",
                    "특징": "필수 가입 보험",
                },
                "종합 자동차보험": {
                    "보장범위": "포괄적인 사고 보장",
                    "보험료": "보통",
                    "특징": "추가 보장 포함",
                },
                "특별 자동차보험": {
                    "보장범위": "최고 수준의 보장",
                    "보험료": "높음",
                    "특징": "프리미엄 서비스",
                },
            }

            response = "보험 상품 비교:\n\n"

            for product in products:
                if product in comparison_data:
                    data = comparison_data[product]
                    response += f"[{product}]\n"
                    response += f"보장범위: {data['보장범위']}\n"
                    response += f"보험료: {data['보험료']}\n"
                    response += f"특징: {data['특징']}\n\n"
                else:
                    response += f"[{product}]\n정보 없음\n\n"

            return response

        except Exception as e:
            logger.error(f"보험 상품 비교 실패: {e}")
            return f"상품 비교 중 오류가 발생했습니다: {str(e)}"

    def _ml_recommendation_system(self, user_info: str) -> str:
        """ML 추천 시스템"""
        try:
            if self.ml_service is None:
                return "ML 추천 시스템이 초기화되지 않았습니다."

            # 사용자 정보 파싱
            parsed_info = self._parse_user_info(user_info)

            if not parsed_info:
                return "사용자 정보를 파싱할 수 없습니다."

            user_id = parsed_info.get("user_id", 1)
            user_profile = {
                "age": parsed_info.get("age", 30),
                "gender": parsed_info.get("gender", 0),
                "driving_experience": parsed_info.get("driving_experience", 5),
                "annual_mileage": parsed_info.get("annual_mileage", 12000),
                "accident_history": parsed_info.get("accident_history", 0),
            }

            # ML 추천 생성
            recommendations = self.ml_service.generate_recommendations(
                user_id, user_profile
            )

            if not recommendations or not recommendations.get("recommended_products"):
                return "ML 추천을 생성할 수 없습니다."

            response = f"ML 추천 시스템 결과 (사용자 ID: {user_id}):\n\n"

            # ML 점수 표시
            ml_scores = recommendations.get("ml_scores", {})
            if ml_scores:
                response += "ML 점수:\n"
                response += (
                    f"- 협업 필터링: {ml_scores.get('collaborative_score', 0):.2f}\n"
                )
                response += f"- 콘텐츠 기반: {ml_scores.get('content_score', 0):.2f}\n"
                response += f"- 하이브리드: {ml_scores.get('hybrid_score', 0):.2f}\n\n"

            # 추천 상품 표시
            products = recommendations.get("recommended_products", [])
            if products:
                response += "추천 상품 (상위 3개):\n"
                for i, product in enumerate(products[:3], 1):
                    response += (
                        f"{i}. {product.get('product_name', '알 수 없는 상품')} "
                    )
                    response += f"(점수: {product.get('hybrid_score', 0):.2f})\n"

            # 유사 사용자 표시
            similar_users = recommendations.get("similar_users", [])
            if similar_users:
                response += f"\n유사 사용자: {len(similar_users)}명"

            return response

        except Exception as e:
            logger.error(f"ML 추천 시스템 실패: {e}")
            return f"ML 추천 생성 중 오류가 발생했습니다: {str(e)}"

    def _analyze_user_profile(self, user_info: str) -> str:
        """사용자 프로필 분석"""
        try:
            # 사용자 정보 파싱
            parsed_info = self._parse_user_info(user_info)

            if not parsed_info:
                return "사용자 정보를 파싱할 수 없습니다."

            # 프로필 특성 분석
            characteristics = self._analyze_profile_characteristics(parsed_info)

            response = f"사용자 프로필 분석 결과:\n\n"
            response += f"기본 정보: {parsed_info.get('age', 0)}세, "
            response += f"운전경력 {parsed_info.get('driving_experience', 0)}년, "
            response += f"연간주행거리 {parsed_info.get('annual_mileage', 0)}km\n\n"

            response += "프로필 특성:\n"
            for char in characteristics:
                response += f"- {char}\n"

            return response

        except Exception as e:
            logger.error(f"사용자 프로필 분석 실패: {e}")
            return f"프로필 분석 중 오류가 발생했습니다: {str(e)}"

    def _analyze_profile_characteristics(self, profile: Dict[str, Any]) -> List[str]:
        """프로필 특성 분석"""
        characteristics = []

        age = profile.get("age", 30)
        driving_experience = profile.get("driving_experience", 5)
        annual_mileage = profile.get("annual_mileage", 12000)
        accident_history = profile.get("accident_history", 0)

        # 나이 기반 특성
        if age < 25:
            characteristics.append("젊은 운전자 - 높은 사고 위험, 보험료 할증 가능")
        elif age > 50:
            characteristics.append("시니어 운전자 - 안전 운전 경향, 할인 혜택 가능")

        # 운전 경력 기반 특성
        if driving_experience < 3:
            characteristics.append("초보 운전자 - 추가 교육 필요, 특별 보장 권장")
        elif driving_experience > 10:
            characteristics.append("베테랑 운전자 - 안전 운전 기록, 할인 혜택")

        # 주행거리 기반 특성
        if annual_mileage > 15000:
            characteristics.append("고주행 운전자 - 높은 사고 위험, 종합보험 권장")
        elif annual_mileage < 8000:
            characteristics.append("저주행 운전자 - 낮은 사고 위험, 기본보험 적합")

        # 사고 이력 기반 특성
        if accident_history > 0:
            characteristics.append("사고 이력 있음 - 보험료 할증, 특별 관리 필요")

        return characteristics

    def _parse_user_info(self, user_info: str) -> Optional[Dict[str, Any]]:
        """사용자 정보 파싱"""
        try:
            # 정규표현식을 사용한 정보 추출
            age_match = re.search(r"(\d+)\s*세", user_info)
            gender_match = re.search(r"([남여]성|M|F)", user_info)
            driving_match = re.search(r"운전\s*경력\s*(\d+)", user_info)
            mileage_match = re.search(r"연간\s*주행거리\s*(\d+)", user_info)
            accident_match = re.search(r"사고\s*이력\s*(\d+)", user_info)
            user_id_match = re.search(r"사용자\s*ID\s*(\d+)", user_info)

            parsed = {}

            if age_match:
                parsed["age"] = int(age_match.group(1))
            if gender_match:
                gender = gender_match.group(1)
                parsed["gender"] = 1 if gender in ["남성", "M"] else 0
            if driving_match:
                parsed["driving_experience"] = int(driving_match.group(1))
            if mileage_match:
                parsed["annual_mileage"] = int(mileage_match.group(1))
            if accident_match:
                parsed["accident_history"] = int(accident_match.group(1))
            if user_id_match:
                parsed["user_id"] = int(user_id_match.group(1))

            return parsed if parsed else None

        except Exception as e:
            logger.error(f"사용자 정보 파싱 실패: {e}")
            return None

    def chat_with_agent(self, user_message: str) -> str:
        """에이전트와 대화"""
        try:
            if self.agent is None:
                return "AI 상담사가 초기화되지 않았습니다."

            response = self.agent.run(user_message)
            return response

        except Exception as e:
            logger.error(f"에이전트 대화 실패: {e}")
            return f"대화 중 오류가 발생했습니다: {str(e)}"

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 이력 조회"""
        try:
            if self.memory is None:
                return []

            history = []
            for message in self.memory.chat_memory.messages:
                if hasattr(message, "content"):
                    role = "user" if message.type == "human" else "assistant"
                    history.append({"role": role, "content": message.content})

            return history

        except Exception as e:
            logger.error(f"대화 이력 조회 실패: {e}")
            return []

    def clear_memory(self):
        """대화 메모리 초기화"""
        try:
            if self.memory:
                self.memory.clear()
                logger.info("대화 메모리 초기화 완료")
        except Exception as e:
            logger.error(f"메모리 초기화 실패: {e}")

    def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 조회"""
        try:
            return {
                "llm_available": self.llm is not None,
                "memory_available": self.memory is not None,
                "agent_available": self.agent is not None,
                "tools_count": len(self.tools),
                "rag_service_available": self.rag_service is not None,
                "ml_service_available": self.ml_service is not None,
            }
        except Exception as e:
            logger.error(f"서비스 상태 조회 실패: {e}")
            return {}
