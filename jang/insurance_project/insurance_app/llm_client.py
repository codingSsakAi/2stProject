# -*- coding: utf-8 -*-
"""
OpenAI LLM 클라이언트 (Django 프로젝트용)
- Responses API 우선
- 폴백: 신형 chat.completions (max_completion_tokens 사용)
- 구형 ChatCompletion 경로 완전 제거 (openai>=1.0.0 호환)
- Pylance 타입 경고 해결(TYPE_CHECKING + TypeAlias)
- 요약/사유 정확한 줄수 보정

공개 함수:
  - summarize_text(clause_text) -> str
  - generate_recommendation_reason(insurer, premium, matched_terms, missing_terms) -> str
  - llm_answer_ko(prompt) -> str
"""

from typing import Optional, List, TYPE_CHECKING, TypeAlias
import os
import re

from django.conf import settings
import openai  # 폴백 경로: chat.completions 전용(신형)

# 타입 체커 전용 별칭
if TYPE_CHECKING:
    from openai import OpenAI as OpenAIClient  # type: ignore[reportMissingImports]
else:
    from typing import Any as _Any
    OpenAIClient: TypeAlias = _Any  # 런타임 Any

# Responses API 런타임 클래스 (타입 별칭과 분리)
try:
    from openai import OpenAI as SDKOpenAI
    _HAS_RESPONSES_API = True
except Exception:
    SDKOpenAI = None  # type: ignore[assignment]
    _HAS_RESPONSES_API = False

OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
MODEL_NAME = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = 0.2

# 신형 openai 모듈에 키 주입 (chat.completions 경로 사용)
openai.api_key = OPENAI_API_KEY

_client: Optional[OpenAIClient] = None

def _client_instance() -> Optional[OpenAIClient]:
    """Responses API 클라이언트 인스턴스(있으면 재사용)"""
    global _client
    if not _HAS_RESPONSES_API:
        return None
    if _client is None:
        if not OPENAI_API_KEY:
            return None
        _client = SDKOpenAI(api_key=OPENAI_API_KEY)  # type: ignore[call-arg]
    return _client

# ────────────────────────────────────────────────────────────────
# 출력 정리/줄수 보정
# ────────────────────────────────────────────────────────────────
_CODE_FENCE = re.compile(r"^\s*```.*?$|```$", re.M)

def _clean_text(s: str) -> str:
    if not s:
        return ""
    t = _CODE_FENCE.sub("", s.strip())
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"([!?~….,])\1{1,}", r"\1", t)
    return t.strip()

def _ensure_n_lines(text: str, n: int) -> str:
    """모델 출력이 형식을 어겨도 정확히 n줄이 되도록 보정"""
    t = _clean_text(text)
    # 불릿/숫자 머리표 제거 + 빈줄 제거
    lines = [re.sub(r"^\s*([-\*\u2022·•○●▶▷]|\(?\d+[\.\)])\s*", "", ln).strip()
             for ln in t.splitlines()]
    lines = [ln for ln in lines if ln]

    if len(lines) < n:
        # 간단 문장 분할로 보충
        rest = re.split(r"(?<=[\.!?]|다|요)\s+", t)
        rest = [x.strip() for x in rest if x.strip()]
        seen = set(lines)
        for s in rest:
            if s in seen:
                continue
            lines.append(s)
            seen.add(s)
            if len(lines) >= n:
                break

    if len(lines) > n:
        lines = lines[:n]

    return "\n".join(lines)

# ────────────────────────────────────────────────────────────────
# 코어 호출: Responses API → chat.completions(신형) 폴백
# ────────────────────────────────────────────────────────────────
def _call_responses_api(user_content: str, system: Optional[str] = None,
                        model: Optional[str] = None,
                        max_output_tokens: int = 600,
                        temperature: float = TEMPERATURE) -> str:
    client = _client_instance()
    if client is None:
        raise RuntimeError("Responses API 클라이언트가 준비되지 않았습니다.")
    mdl = model or MODEL_NAME
    resp = client.responses.create(
        model=mdl,
        input=(
            [{"role": "system", "content": system}] if system else []
        ) + [{"role": "user", "content": user_content}],
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    text = getattr(resp, "output_text", None)
    if text:
        return text.strip()

    # 폴백 파싱
    try:
        chunks: List[str] = []
        for item in (resp.output or []):
            for c in (item.get("content") or []):
                if c.get("type") == "output_text":
                    chunks.append(c.get("text") or "")
        if chunks:
            return "\n".join(chunks).strip()
    except Exception:
        pass
    return str(resp)

def _call_chat_api_new(user_content: str, system: Optional[str] = None,
                       model: Optional[str] = None,
                       max_tokens: int = 600,
                       temperature: float = TEMPERATURE) -> str:
    """
    신형 chat.completions 폴백 (openai>=1.0.0)
    - 파라미터: max_completion_tokens 사용
    - 구형 ChatCompletion.create 는 사용하지 않음
    """
    mdl = model or MODEL_NAME
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_content})

    # 기본: max_completion_tokens
    try:
        resp = openai.chat.completions.create(
            model=mdl,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        return (content or "").strip()
    except TypeError:
        # 일부 배포본이 아직 max_completion_tokens 미지원인 경우 max_tokens로 재시도
        resp = openai.chat.completions.create(
            model=mdl,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        return (content or "").strip()

def _generate_text(user_content: str, system: Optional[str] = None,
                   model: Optional[str] = None,
                   max_output_tokens: int = 600,
                   temperature: float = TEMPERATURE) -> str:
    if not OPENAI_API_KEY:
        return "LLM API 키가 설정되지 않았습니다(OPENAI_API_KEY)."

    # 1) Responses API 우선
    if _HAS_RESPONSES_API:
        try:
            return _clean_text(
                _call_responses_api(
                    user_content=user_content,
                    system=system,
                    model=model,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                )
            )
        except Exception:
            pass  # 폴백

    # 2) 신형 chat.completions 폴백
    try:
        return _clean_text(
            _call_chat_api_new(
                user_content=user_content,
                system=system,
                model=model,
                max_tokens=max_output_tokens,
                temperature=temperature,
            )
        )
    except Exception as e:
        return f"일반 답변 생성 중 오류가 발생했습니다: {e}"

# ────────────────────────────────────────────────────────────────
# 공개 API
# ────────────────────────────────────────────────────────────────
def summarize_text(clause_text: str) -> str:
    """약관을 보장 범위/제한 조건/유의사항 중심으로 '정확히 3줄' 요약"""
    system = (
        "너는 한국어 보험 약관 요약 도우미다. 과장 금지, 사실 기반. "
        "출력은 정확히 3줄, 각 줄은 하나의 완결 문장. 불릿/기호 사용 금지."
    )
    prompt = (
        "다음 자동차보험 약관을 보장 범위·제한 조건·유의사항 위주로 3줄 요약:\n\n"
        f"{clause_text}"
    )
    raw = _generate_text(prompt, system=system, model=MODEL_NAME, max_output_tokens=500)
    return _ensure_n_lines(raw, 3)

def generate_recommendation_reason(insurer: str, premium: str,
                                   matched_terms, missing_terms) -> str:
    """추천 사유를 '정확히 2줄'로 요약"""
    system = (
        "너는 자동차보험 추천 사유를 간결히 작성하는 도우미다. "
        "출력은 정확히 2줄, 각 줄은 하나의 완결 문장. 불릿/기호 사용 금지."
    )
    prompt = (
        f"보험사: {insurer}\n"
        f"보험료: {premium}원\n"
        f"포함 특약: {matched_terms}\n"
        f"부족 특약: {missing_terms}\n\n"
        "위 정보를 바탕으로 추천 사유를 2줄로 요약해줘."
    )
    raw = _generate_text(prompt, system=system, model=MODEL_NAME, max_output_tokens=300)
    return _ensure_n_lines(raw, 2)

def llm_answer_ko(prompt: str) -> str:
    """일반 한국어 답변(정리/설명형)"""
    system = (
        "너는 한국어 보험 도메인 어시스턴트다. 질문에 간결하고 자연스럽게 답하고, "
        "불확실한 부분은 '회사·상품별로 상이'라고 안내한다. "
        "허위 근거/페이지를 생성하지 말고, 과장·마케팅 문구를 피하라."
    )
    return _generate_text(prompt, system=system, model=MODEL_NAME, max_output_tokens=700)
