import requests
from bs4 import BeautifulSoup
import json
import os

BASE_URL = 'https://bigin.kidi.or.kr:9443'
LIST_URL = BASE_URL + '/info/getWeeklyInfoList?selClassification=&selDetail=A&searchWord=%EC%9E%90%EB%8F%99%EC%B0%A8&pageNo=1'
SAVE_JSON = os.path.join(os.path.dirname(__file__), 'weekly_articles.json')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

session = requests.Session()
session.verify = False

res = session.get(LIST_URL, headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

articles = []
# 목록은 li 단위로
for li in soup.select('li'):
    a_tag = li.select_one('a[href^="/info/getWeeklyInfoDetail"]')
    thumb_ttl = li.select_one('.thumb_ttl')
    em_tag = li.select_one('em')
    if not (a_tag and thumb_ttl):
        continue
    detail_url = BASE_URL + a_tag['href']
    title = thumb_ttl.get_text(strip=True)
    category = em_tag.get_text(strip=True) if em_tag else ''
    
    # 상세 페이지 크롤링
    detail_res = session.get(detail_url, headers=headers)
    detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
    # 상세: em, h4, strong, p 태그 모두 추출
    main_em = detail_soup.select_one('em')
    main_h4 = detail_soup.select_one('h4')
    main_strongs = [s.get_text(strip=True) for s in detail_soup.select('strong')]
    main_ps = [p.get_text(strip=True) for p in detail_soup.select('p')]

    articles.append({
        'title': title,
        'category': category,
        'url': detail_url,
        'main_em': main_em.get_text(strip=True) if main_em else '',
        'main_h4': main_h4.get_text(strip=True) if main_h4 else '',
        'main_strongs': main_strongs,
        'main_ps': main_ps,
    })

    if len(articles) >= 6:
        break

with open(SAVE_JSON, 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f'크롤링 완료: {len(articles)}개 저장 ({SAVE_JSON})')
