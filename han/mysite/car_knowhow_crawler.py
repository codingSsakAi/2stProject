import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://bigin.kidi.or.kr:9443'
LIST_URL = f'{BASE_URL}/info/getWeeklyInfoList?selClassification=&selDetail=A&searchWord=자동차&pageNo=1'

# 1. 목록 페이지 크롤링
res = requests.get(LIST_URL, verify=False)  # SSL 우회 필요할 수 있음
soup = BeautifulSoup(res.text, 'html.parser')

# 2. 각 카드의 상세페이지 링크 추출 (여기서 직접 URL 확인 필요)
links = []  # 상세페이지 링크를 담을 리스트
for a in soup.select('.listBody .listBox .subject a'):
    href = a.get('href')
    if href:
        links.append(BASE_URL + href)

# 3. 상세페이지에서 제목, 요약, 본문, 이미지 추출
for link in links:
    res = requests.get(link, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.select_one('.subject').text.strip()
    summary = soup.select_one('.desc').text.strip()  # 예시, 실제 구조에 맞게
    content = soup.select_one('.conBody').text.strip()
    img = soup.select_one('.weekly-img img')
    image_url = BASE_URL + img['src'] if img else None

    # 결과 출력 or 저장
    print({'title': title, 'summary': summary, 'content': content, 'image': image_url})
