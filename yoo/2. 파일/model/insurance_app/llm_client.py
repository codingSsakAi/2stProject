import openai
from django.conf import settings
openai.api_key = settings.OPENAI_API_KEY

def summarize_text(clause_text):
    prompt = f"다음 자동차보험 약관을 보장 범위/제한 조건/유의사항 위주로 3줄 요약:\n\n{clause_text}"
    response = openai.ChatCompletion.create(model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message["content"]

def generate_recommendation_reason(insurer, premium, matched_terms, missing_terms):
    prompt = f"보험사: {insurer}, 보험료: {premium}원, 포함 특약: {matched_terms}, 부족 특약: {missing_terms}.\n추천 사유를 2줄로 요약."
    response = openai.ChatCompletion.create(model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message["content"]
