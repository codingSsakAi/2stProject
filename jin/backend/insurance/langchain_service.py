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

    def _parse_user_info(self, user_info: str) -> Dict[str, Any]:
        """사용자 정보 파싱"""
        profile = {
            "age": None,
            "gender": None,
            "occupation": None,
            "income_level": None,
            "family_status": None,
            "health_condition": None,
            "driving_experience": None
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
            보험 관련 정보를 제공할 때는 정확하고 이해하기 쉽게 설명해주세요."""

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
            "rag_service_available": self.rag_service is not None
        } 