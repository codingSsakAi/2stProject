# insurance_portal/views/chatbot.py

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import os
import openai
from pinecone import Pinecone

# 환경 변수 로드
PINECONE_API_KEY_MY = os.getenv("PINECONE_API_KEY_MY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
pc = Pinecone(api_key=PINECONE_API_KEY_MY)
index = pc.Index(INDEX_NAME)


def get_openai_embedding(text):
    """
    OpenAI 임베딩 생성
    """
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    return response.data[0].embedding


def search_fault_ratio(query, top_k=5):
    """
    Pinecone에서 과실비율 안내 문서 검색
    """
    query_emb = get_openai_embedding(query)
    result = index.query(
        vector=query_emb,
        top_k=top_k,
        include_metadata=True,
    )

    matches = []
    for m in result.get("matches", []):
        meta = m.get("metadata", {})
        matches.append({
            "score": round(m.get("score", 0) * 100, 2),  # 퍼센트 표시
            "chunk": meta.get("text", ""),
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
        })
    return matches


def recommendation_view(request):
    """
    과실 챗봇 UI 페이지
    """
    return render(request, "insurance_portal/recommendation.html")


@csrf_exempt
def fault_chatbot_api(request):
    """
    과실 챗봇 API
    """
    query = request.GET.get("q") or request.POST.get("q", "")
    if not query:
        return JsonResponse({"error": "질문이 비어 있습니다."}, status=400)

    # 1. Pinecone 검색
    matches = search_fault_ratio(query)

    # 2. LLM 응답 생성 (간단 예시)
    #    - 실제 환경에서는 matches 내용을 LLM 프롬프트에 삽입해 요약/가공
    context_texts = [m["chunk"] for m in matches]
    context = "\n\n".join(context_texts)

    prompt = f"""
다음은 교통사고 과실비율 안내서의 일부 내용입니다. 사용자의 질문에 답해주세요.
질문: {query}
참고자료:
{context}
"""

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 한국 교통사고 과실비율 안내 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        answer_text = completion.choices[0].message["content"].strip()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    # 3. 최종 답변에 링크 추가
    final_answer = answer_text.rstrip()
    final_answer += "\n\n정확한 과실비율은 여기에서 확인하세요: https://accident.knia.or.kr/myaccident1"

    # 4. 유사도 상위 결과 일부도 같이 반환 가능
    return JsonResponse({
        "answer": final_answer,
        "matches": matches[:3]  # 상위 3개만 예시로 반환
    })