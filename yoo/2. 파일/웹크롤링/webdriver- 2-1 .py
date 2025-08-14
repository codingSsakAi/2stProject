# -*- coding: utf-8 -*-
"""
과실비율 FAQ / 용어해설 크롤러
사이트: https://accident.knia.or.kr/faq#0  (FAQ 탭)
      : https://accident.knia.or.kr/define  (용어해설 탭)

수집 결과:
- accident_knia_faq.json / .csv   : 질문/답변
- accident_knia_terms.json / .csv : 용어/설명

필요 패키지: selenium, beautifulsoup4 (설치됨 가정)
"""

import re
import csv
import json
import time
from datetime import datetime
from collections import OrderedDict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)

WAIT = 10

FAQ_URL = "https://accident.knia.or.kr/faq#0"
DEFINE_URL = "https://accident.knia.or.kr/define"

OUT_FAQ_JSON   = "accident_knia_faq.json"
OUT_FAQ_CSV    = "accident_knia_faq.csv"
OUT_TERM_JSON  = "accident_knia_terms.json"
OUT_TERM_CSV   = "accident_knia_terms.csv"


# -------------------------- 공통 유틸 --------------------------

def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--window-size=1400,2200")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts, service=Service())
    driver.set_page_load_timeout(30)
    return driver


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def save_json_csv(records, json_path, csv_path, fieldnames):
    # JSON (UTF-8)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # CSV (UTF-8-SIG: 엑셀 호환)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(records)


def wait_body(driver):
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def exists(driver, by, sel) -> bool:
    try:
        driver.find_element(by, sel)
        return True
    except Exception:
        return False


# -------------------------- 1) 과실비율 FAQ --------------------------
"""
구조(설명 주신 그대로):
- 전체틀: div#faq_frm
- 목록 컨테이너: div.faq_cont.paginated (내부에 Q/A 블록 반복)
- 질문: div.faq_q_frm > div.faq_txt > a   또는
        (질문/답변이 모두 div.faq_a_frm이고 style로 구분될 수 있음)
- 답변: div.faq_a_frm > div.faq_txt > p* (여러 문단)
- 페이지네이션: div#paging_div 안의 button.tb_paging.active 가 '다음' 버튼
"""

def get_first_question_on_page(driver) -> str:
    """현재 페이지 첫 질문 텍스트(페이지 전환 대기 신호)."""
    # 가장 위 Q 텍스트를 안정적으로 잡아 페이지 변경 감지
    try:
        q = driver.find_element(By.CSS_SELECTOR, "div#faq_frm div.faq_q_frm div.faq_txt")
        return clean_text(q.text)
    except Exception:
        pass
    # 폴백: style 기반 구조 (display:block 이 질문)일 때
    try:
        qa = driver.find_elements(By.CSS_SELECTOR, "div#faq_frm div.faq_a_frm")
        for div in qa:
            st = (div.get_attribute("style") or "").replace(" ", "").lower()
            if "display:block" in st:
                t = div.find_element(By.CSS_SELECTOR, "div.faq_txt").text
                if t:
                    return clean_text(t)
    except Exception:
        pass
    return ""


def parse_faq_current_page(driver):
    """
    현재 FAQ 페이지에서
    - 질문 anchor들을 위에서부터 클릭
    - href의 menuclick(faqNN)에서 faqNN을 뽑아 답변 영역(#faqNN) 텍스트 수집
    - 질문 텍스트는 (1) anchor.innerText → (2) 답변 div의 앞 질문 div에서 보강
    """
    results = []

    q_anchors = driver.find_elements(
        By.CSS_SELECTOR, "div#faq_frm div.faq_q_frm div.faq_txt > a"
    )

    for idx in range(len(q_anchors)):
        # 매 반복마다 다시 찾기(스테일 방지)
        a = driver.find_elements(
            By.CSS_SELECTOR, "div#faq_frm div.faq_q_frm div.faq_txt > a"
        )[idx]

        # 질문 텍스트 (우선: innerText, 보조: text)
        q_text = (a.get_attribute("innerText") or "").strip()
        if not q_text:
            q_text = (a.text or "").strip()

        # 답변 id 뽑기: javascript:menuclick(faq62);
        href = a.get_attribute("href") or ""
        m = re.search(r"menuclick\(\s*(faq\d+)\s*\)", href)
        ans_id = m.group(1) if m else None

        # 클릭해서 답변 펼치기
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
        except Exception:
            pass
        try:
            a.click()
        except Exception:
            driver.execute_script("arguments[0].click();", a)

        # 답변 div가 보일 때까지 잠깐 대기(가능하면 style 체크)
        if ans_id:
            try:
                WebDriverWait(driver, WAIT).until(
                    lambda d: "display:none" not in (
                        (d.find_element(By.CSS_SELECTOR, f"div#faq_frm div.faq_a_frm#{ans_id}")
                         .get_attribute("style") or "").replace(" ", "").lower()
                    )
                )
            except Exception:
                pass

        # (보강) 질문이 비어 있으면 답변 div의 바로 앞 질문 div에서 텍스트 재추출
        if not q_text and ans_id:
            try:
                q_div = driver.find_element(
                    By.XPATH,
                    f"//div[@id='faq_frm']//div[@id='{ans_id}']"
                    "/preceding-sibling::div[contains(@class,'faq_q_frm')][1]"
                    "//div[contains(@class,'faq_txt')]"
                )
                q_text = (q_div.get_attribute("innerText") or q_div.text or "").strip()
            except Exception:
                pass

        # 답변 텍스트 수집(여러 p를 공백 하나로 연결)
        ans_text = ""
        if ans_id:
            try:
                ans_box = driver.find_element(
                    By.CSS_SELECTOR, f"div#faq_frm div.faq_a_frm#{ans_id} div.faq_txt"
                )
                ps = ans_box.find_elements(By.TAG_NAME, "p")
                if ps:
                    ans_text = " ".join(
                        [(p.get_attribute("innerText") or p.text or "").strip()
                         for p in ps if (p.get_attribute("innerText") or p.text or "").strip()]
                    ).strip()
                else:
                    ans_text = (ans_box.get_attribute("innerText") or ans_box.text or "").strip()
            except Exception:
                pass
        else:
            # 안전 폴백: 질문 블록의 다음 형제 답변 div에서 추출
            try:
                ans_div = a.find_element(By.XPATH, "../../following-sibling::div[contains(@class,'faq_a_frm')][1]")
                ps = ans_div.find_elements(By.CSS_SELECTOR, "div.faq_txt p")
                if ps:
                    ans_text = " ".join(
                        [(p.get_attribute("innerText") or p.text or "").strip()
                         for p in ps if (p.get_attribute("innerText") or p.text or "").strip()]
                    ).strip()
                else:
                    box = ans_div.find_element(By.CSS_SELECTOR, "div.faq_txt")
                    ans_text = (box.get_attribute("innerText") or box.text or "").strip()
            except Exception:
                pass
            q_text  = clean_text(q_text).replace("\u00a0", " ")
            ans_text = clean_text(ans_text).replace("\u00a0", " ")
        results.append((q_text, ans_text))

    return results

    # 2) 폴백: a_frm 스타일 짝짓기
    qa_divs = driver.find_elements(By.CSS_SELECTOR, "div#faq_frm div.faq_a_frm")
    i = 0
    while i < len(qa_divs) - 1:
        try:
            q_div = qa_divs[i]
            a_div = qa_divs[i+1]
            q_style = (q_div.get_attribute("style") or "").replace(" ", "").lower()
            a_style = (a_div.get_attribute("style") or "").replace(" ", "").lower()

            # 질문: display:block / 답변: display:none 가정
            if "display:block" in q_style and "display:none" in a_style:
                q_txt = clean_text(q_div.find_element(By.CSS_SELECTOR, "div.faq_txt").text)
                ps = a_div.find_elements(By.CSS_SELECTOR, "div.faq_txt p")
                if ps:
                    a_txt = clean_text(" ".join([clean_text(p.text) for p in ps if clean_text(p.text)]))
                else:
                    a_txt = clean_text(a_div.find_element(By.CSS_SELECTOR, "div.faq_txt").text)

                if q_txt or a_txt:
                    results.append((q_txt, a_txt))
                i += 2
                continue
        except Exception:
            pass

        i += 1

    return results


def click_faq_next_page(driver) -> bool:
    """
    FAQ '다음 페이지' 클릭.
    1순위: #paging_div 내 텍스트가 '다음'인 버튼/링크
    2순위: #paging_div 내 img alt에 '다음' 포함
    3순위: #paging_div 내 .tb_paging 중 숫자 기반(next = 현재+1)
    클릭 후 첫 질문 텍스트가 바뀔 때까지 대기.
    """
    prev_first = get_first_question_on_page(driver)

    # 1) 텍스트 '다음'
    x_next = "//div[@id='paging_div']//*[self::button or self::a][normalize-space(text())='다음']"
    cand = driver.find_elements(By.XPATH, x_next)
    if not cand:
        # 2) 이미지 alt='다음'
        x_next_img = "//div[@id='paging_div']//*[self::button or self::a][.//img[contains(@alt,'다음')]]"
        cand = driver.find_elements(By.XPATH, x_next_img)

    # 3) 숫자 기반(현재 n → n+1)
    if not cand:
        # 현재 페이지 번호
        cur = None
        nums = driver.find_elements(By.CSS_SELECTOR, "#paging_div .tb_paging")
        for e in nums:
            txt = (e.text or "").strip()
            cls = (e.get_attribute("class") or "").lower()
            if txt.isdigit() and ("on" in cls or "active" in cls):
                cur = int(txt)
                break
        if cur is not None:
            # n+1 찾기
            for e in nums:
                txt = (e.text or "").strip()
                if txt.isdigit() and int(txt) == cur + 1:
                    cand = [e]
                    break

    for el in cand:
        try:
            # 비활성 처리 스킵
            cls = (el.get_attribute("class") or "").lower()
            dis = el.get_attribute("disabled")
            if dis or "disabled" in cls:
                continue

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.05)
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)

            WebDriverWait(driver, WAIT).until(
                lambda d: (get_first_question_on_page(d) or "") != prev_first
            )
            time.sleep(0.15)
            return True
        except Exception:
            continue

    return False


def crawl_faq_all(headless=True):
    driver = make_driver(headless=headless)
    driver.get(FAQ_URL)
    wait_body(driver)
    time.sleep(0.3)

    faq_map = []  # 순서 유지용 리스트

    while True:
        # 1) 현재 페이지의 10개 질문을 '클릭 → 답변 추출'로 수집
        pairs = parse_faq_current_page(driver)  # (q, a) 튜플 리스트
        for q, a in pairs:
            faq_map.append({"question": q, "answer": a})

        # 2) 다음 페이지로 이동(못 가면 종료)
        moved = click_faq_next_page(driver)
        if not moved:
            break

    driver.quit()

    # (선택) 저장까지 여기서 처리
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = [
        {"id": i+1, "question": row["question"], "answer": row["answer"],
         "source": "KNIA 과실비율 FAQ", "collected_date": ts}
        for i, row in enumerate(faq_map)
    ]
    save_json_csv(records, OUT_FAQ_JSON, OUT_FAQ_CSV,
                  fieldnames=["id", "question", "answer", "source", "collected_date"])
    print(f"[FAQ] 총 {len(records)}건 저장 → {OUT_FAQ_JSON}, {OUT_FAQ_CSV}")

    # 레코드화
    records = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i, row in enumerate(faq_map, 1):
        records.append({
            "id": i,
            "question": row["question"],
            "answer": row["answer"],
            "source": "KNIA 과실비율 FAQ",
            "collected_date": ts,
        })

# -------------------------- 2) 과실비율 용어해설 --------------------------
"""
구조(설명 주신 그대로):
- 리스트 페이지 전체틀: div#subcontent > div#faq_frm
- 표 tbody#ContentResult 안에 tr 들
- 각 tr의 td.tb_title a 를 클릭하면 상세로 이동 (예: /define-content?index=87890)
- 상세 페이지:
  - 용어명칭: div.bbsview_title
  - 용어설명: div.bbsview_cate 아래 p* 여러 개 가능
- 페이지당 10개 → 10개 클릭-수집-뒤로, 다음 버튼으로 다음 목록
- 페이지네이션 컨테이너: div#paging_div
  - 다음 버튼 선택 기준은 FAQ와 동일하게 button.tb_paging.active 사용(전달받은 기준)
"""

def wait_define_list_loaded(driver):
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody#ContentResult tr"))
    )
    time.sleep(0.1)


def get_define_rows(driver):
    return driver.find_elements(By.CSS_SELECTOR, "tbody#ContentResult tr")


def open_define_detail_by_row_index(driver, idx: int) -> bool:
    rows = get_define_rows(driver)
    if idx < 0 or idx >= len(rows):
        return False
    row = rows[idx]
    try:
        a = row.find_element(By.CSS_SELECTOR, "td.tb_title a")
    except Exception:
        return False

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
    time.sleep(0.05)
    try:
        a.click()
    except Exception:
        driver.execute_script("arguments[0].click();", a)

    # 상세 페이지 로딩 대기 (제목이 나타날 때)
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.bbsview_title"))
    )
    time.sleep(0.1)
    return True


def parse_define_detail(driver):
    try:
        term = clean_text(driver.find_element(By.CSS_SELECTOR, "div.bbsview_title").text)
    except Exception:
        term = ""
    # 설명: div.bbsview_cate 아래 p*
    desc = ""
    try:
        ps = driver.find_elements(By.CSS_SELECTOR, "div.bbsview_cate p")
        if ps:
            desc = clean_text(" ".join([clean_text(p.text) for p in ps if clean_text(p.text)]))
        else:
            # 보조: 본문 전체 텍스트
            desc = clean_text(driver.find_element(By.CSS_SELECTOR, "div.bbsview_cate").text)
    except Exception:
        pass
    return term, desc


def go_back_to_define_list(driver):
    driver.back()
    wait_define_list_loaded(driver)


def click_define_next_page(driver) -> bool:
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, "div#paging_div button.tb_paging.active")
        if not btns:
            return False
        btn = btns[0]
        cls = (btn.get_attribute("class") or "").lower()
        dis = btn.get_attribute("disabled")
        if dis or "disabled" in cls:
            return False

        # 현재 첫 행의 제목(미리) → 페이지 전환 대기 신호로 사용
        try:
            first_text = clean_text(
                driver.find_element(By.CSS_SELECTOR, "tbody#ContentResult tr td.tb_title a").text
            )
        except Exception:
            first_text = ""

        driver.execute_script("arguments[0].click();", btn)

        def changed(d):
            try:
                now = clean_text(
                    d.find_element(By.CSS_SELECTOR, "tbody#ContentResult tr td.tb_title a").text
                )
                return now and now != first_text
            except Exception:
                return False

        WebDriverWait(driver, WAIT).until(changed)
        time.sleep(0.2)
        return True
    except Exception:
        return False


def crawl_define_all(headless=True):
    driver = make_driver(headless=headless)
    driver.get(DEFINE_URL)
    wait_body(driver)
    wait_define_list_loaded(driver)

    results = OrderedDict()  # term -> description

    while True:
        rows = get_define_rows(driver)
        n = len(rows)
        for i in range(n):
            # 매 루프마다 다시 rows 조회하지 않으면 back() 후 stale 발생 가능
            ok = open_define_detail_by_row_index(driver, i)
            if not ok:
                continue
            term, desc = parse_define_detail(driver)
            if term and desc and term not in results:
                results[term] = desc
            go_back_to_define_list(driver)

        moved = click_define_next_page(driver)
        if not moved:
            break

    driver.quit()

    # 레코드화 및 저장
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recs = []
    for i, (term, desc) in enumerate(results.items(), 1):
        recs.append({
            "id": i,
            "term": term,
            "description": desc,
            "source": "KNIA 과실비율 용어해설",
            "collected_date": ts,
        })

    save_json_csv(recs, OUT_TERM_JSON, OUT_TERM_CSV,
                  fieldnames=["id", "term", "description", "source", "collected_date"])
    print(f"[용어해설] 총 {len(recs)}건 저장 → {OUT_TERM_JSON}, {OUT_TERM_CSV}")


# -------------------------- 실행 진입 --------------------------

if __name__ == "__main__":
    # 창 보이려면 headless=False
    crawl_faq_all(headless=True)
    crawl_define_all(headless=True)
