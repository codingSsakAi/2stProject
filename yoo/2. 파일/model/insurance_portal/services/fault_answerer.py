# -*- coding: utf-8 -*-
"""
프롬프트(SYSTEM/USER) 적용 → RAG 소스 정렬/포맷 → LLM 호출 → JSON 파싱/스키마 강제 → 결과 리턴.
- 대화 히스토리 지원 추가
- 모델 일탈 방지: response_format=json_object 시도 + 파싱 보정
- 재질문/최종답변 분기 강제: needs_more_input에 따라 필드 비움/채움 규칙 적용
- 로깅: 프롬프트 해시, 요청/응답 요약
"""
import os, json, re, time, hashlib, logging
from typing import List, Dict, Any, Tuple, Optional

# 프롬프트 원본
from insurance_portal.services.prompt_fault import SYSTEM_PROMPT, USER_PROMPT  # 경로는 프로젝트에 맞춰 조정
# Pinecone 검색 래퍼
from insurance_portal.services.pinecone_search_fault import retrieve_fault_sources  # 아래 4)에서 alias 보강

logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
TOP_K = int(os.getenv("FAULT_TOP_K", "7"))

def _chat_completion(messages: List[Dict[str, str]], model: str) -> str:
    """OpenAI SDK 신/구버전 공용 호출"""
    try:
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content
    except Exception:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
        )
        return resp["choices"][0]["message"]["content"]

def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _json_coerce(s: str) -> Dict[str, Any]:
    s = _strip_code_fence(s)
    m = re.search(r"\{.*\}\s*$", s, flags=re.S)
    if m:
        s = m.group(0)
    return json.loads(s)

def _format_sources(hits: List[Dict[str, Any]], limit: int = 7) -> Tuple[str, List[Dict[str, Any]]]:
    """표 우선 → 점수순 정렬 후 USER_PROMPT에 넣을 단일 문자열과 인용 메타 생성"""
    def _key(h):
        md = (h.get("metadata") or {})
        has_table = 1 if md.get("table_md") else 0
        return (-has_table, -(h.get("score") or 0.0))

    hits_sorted = sorted(hits, key=_key)[:limit]
    blocks, cits = [], []
    for i, h in enumerate(hits_sorted, 1):
        md = h.get("metadata") or {}
        body = md.get("table_md") or md.get("text") or h.get("text") or ""
        file = md.get("file") or md.get("source") or h.get("file") or ""
        page = md.get("page") or md.get("page_hint") or h.get("page") or ""
        hid = h.get("id") or f"hit_{i}"
        blocks.append(f"[{i}] id={hid} file={file} page={page}\n{body}\n")
        cits.append({"id": hid, "file": file, "page": page, "score": h.get("score", 0)})
    return "\n\n".join(blocks).strip(), cits

def _format_conversation_history(history: List[Dict[str, str]], max_turns: int = 3) -> str:
    """대화 히스토리를 프롬프트용 문자열로 포맷"""
    if not history:
        return ""
    
    # 최근 N턴만 사용 (너무 길면 토큰 제한 문제)
    recent_history = history[-max_turns * 2:] if len(history) > max_turns * 2 else history
    
    formatted = []
    for msg in recent_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            formatted.append(f"사용자: {content}")
        elif role == "assistant":
            formatted.append(f"AI: {content}")
    
    if formatted:
        return f"\n이전 대화 내역:\n" + "\n".join(formatted) + "\n\n"
    return ""

def _enforce_schema(obj: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 스키마 강제: 재질문이면 결과 필드 비우기, 최종답변이면 final_answer 필수"""
    if not isinstance(obj, dict):
        raise ValueError("model output is not a JSON object")

    nmi = bool(obj.get("needs_more_input", False))
    as_str = lambda x: "" if x is None else str(x)
    as_list = lambda x: [] if x is None else list(x)

    if nmi:
        obj["needs_more_input"] = True
        obj["summary"] = as_str(obj.get("summary"))
        obj["followups"] = as_list(obj.get("followups"))[:5]
        obj["table_markdown"] = ""
        obj["final_answer"] = ""
        obj["ratio_table"] = ""
        obj["factors"] = []
        obj["citations"] = []
    else:
        obj["needs_more_input"] = False
        if not obj.get("final_answer"):
            raise ValueError("final_answer is required when needs_more_input=false")
        obj["table_markdown"] = as_str(obj.get("table_markdown"))
        obj["final_answer"] = as_str(obj.get("final_answer"))
        obj["ratio_table"] = as_str(obj.get("ratio_table"))
        obj["factors"] = as_list(obj.get("factors"))
        obj["citations"] = as_list(obj.get("citations"))
        obj["followups"] = as_list(obj.get("followups"))
    return obj

def answer_fault(
    query: str, 
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = TOP_K
) -> Dict[str, Any]:
    """뷰에서 호출하는 진입점 - 대화 히스토리 지원"""
    t0 = time.time()

    hits = retrieve_fault_sources(query, top_k=top_k)
    sources_str, citations_meta = _format_sources(hits, limit=top_k)
    
    # 대화 히스토리 포맷
    history_context = _format_conversation_history(conversation_history or [])
    
    # 프롬프트에 히스토리 추가
    user_content = f"{history_context}현재 질문: {query}\n\n참고자료:\n{sources_str}"

    sys_hash, usr_hash = _h(SYSTEM_PROMPT), _h(user_content)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    
    logger.info("[fault] system_hash=%s user_hash=%s qlen=%d slen=%d history_len=%d",
                sys_hash, usr_hash, len(query), len(sources_str), 
                len(conversation_history or []))

    raw = _chat_completion(messages, OPENAI_MODEL)
    took = (time.time() - t0) * 1000

    try:
        obj = _json_coerce(raw)
    except Exception as e:
        logger.exception("[fault] JSON parse failed: %s; raw_head=%.200s", e, raw)
        raise

    obj = _enforce_schema(obj)

    if (not obj.get("needs_more_input")) and not obj.get("citations"):
        obj["citations"] = citations_meta[:3]

    logger.info("[fault] done needs_more_input=%s took=%.1fms", obj.get("needs_more_input"), took)
    return obj