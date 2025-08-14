# -*- coding: utf-8 -*-
"""
DB생명 생명보험용어사전 크롤러 (수정본)
- URL: https://www.idblife.com/support/knowledge/insurance
- 상단 간편분류(ㄱ~기타) 전부 순회
- 각 분류마다 하단 페이지네이션을 끝까지 순회 (1~10, 다음=11, ...)
- 항목 파싱: div.dic_result > dl > dt(용어)/dd(설명) 페어(한 페이지 5개)
- 저장: JSON(UTF-8, ensure_ascii=False) + CSV(UTF-8-SIG)
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

BASE = "https://www.idblife.com/support/knowledge/insurance"
OUT_JSON = "idblife_insurance_terms.json"
OUT_CSV  = "idblife_insurance_terms.csv"

WAIT = 10

# 간편분류 라벨(순회 순서)
CATS = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ","기타"]


def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--window-size=1400,2000")
    opts.add_argument("--disable-dev-shm-usage")
    # Selenium 4.6+는 드라이버 자동관리
    driver = webdriver.Chrome(options=opts, service=Service())
    driver.set_page_load_timeout(30)
    return driver


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def norm_term(s: str) -> str:
    s = clean_text(s)
    s = re.sub(r'^[#\-\*\s·•\u00B7]+', '', s)
    s = re.sub(r'[\-\*\s·•\u00B7]+$', '', s)
    return s


def body_text(driver) -> str:
    try:
        return driver.find_element(By.TAG_NAME, "body").get_attribute("innerText")
    except Exception:
        return ""


def wait_after_navigation(driver, prev_first_term: str = None):
    """
    탭 전환/페이지 전환 후: 첫 번째 dt(용어) 텍스트가 변하거나
    리스트가 로드될 때까지 대기
    """
    def _changed(d):
        try:
            first_dt = d.find_element(By.CSS_SELECTOR, "div.dic_result dl dt").text
            first_dt = clean_text(first_dt)
            if not prev_first_term:
                return len(first_dt) > 0
            return first_dt != prev_first_term
        except Exception:
            # dt가 일시적으로 없을 수 있음 -> 계속 대기
            return False

    WebDriverWait(driver, WAIT).until(_changed)
    time.sleep(0.2)


def close_popups_if_any(driver):
    try:
        # '닫기' 텍스트 버튼류
        close_buttons = driver.find_elements(By.XPATH, "//button[contains(.,'닫기')] | //a[contains(.,'닫기')]")
        for b in close_buttons:
            try:
                if b.is_displayed() and b.is_enabled():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(0.1)
            except Exception:
                continue
    except Exception:
        pass


def click_category(driver, label: str) -> bool:
    """
    상단 간편분류 클릭
    DOM: div.box_dic_top > div.right > div.classify > a > span=라벨
    """
    close_popups_if_any(driver)

    # label에 작은따옴표가 포함되는 경우 대비해 XPath 리터럴 안전 구성
    # (여기서는 ㄱ~기타라 문제 없지만 일반 안전 처리)
    def _xp_literal(text):
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        # 둘 다 있으면 concat()
        parts = text.split("'")
        return "concat(" + ", \"'\", ".join([f"'{p}'" for p in parts]) + ")"

    lit = _xp_literal(label)
    xp = (
        f"//div[contains(@class,'box_dic_top')]"
        f"//div[contains(@class,'right')]"
        f"//div[contains(@class,'classify')]"
        f"//a[span[normalize-space(text())={lit}]]"
    )
    els = driver.find_elements(By.XPATH, xp)
    for el in els:
        try:
            if el.is_displayed() and el.is_enabled():
                driver.execute_script("arguments[0].click();", el)
                return True
        except Exception:
            continue
    return False


def get_first_term_text(driver) -> str:
    try:
        return clean_text(driver.find_element(By.CSS_SELECTOR, "div.dic_result dl dt").text)
    except Exception:
        return ""


def collect_current_page_items(driver):
    """
    div.dic_result > dl > [dt, dd]를 순서대로 페어링하여 5개 추출
    """
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    res = []

    dic = soup.select_one("div.dic_result dl")
    if not dic:
        return res

    dts = dic.select("dt")
    dds = dic.select("dd")

    n = min(len(dts), len(dds))
    for i in range(n):
        term = norm_term(dts[i].get_text(" ", strip=True))
        desc = clean_text(dds[i].get_text(" ", strip=True))
        if term and desc:
            res.append((term, desc))

    return res


def get_current_page_number(driver) -> int:
    """
    하단 페이지네이션: 현재 페이지 번호 읽기
    DOM 예: <a href="#" data-page="1" class="page on disabled"><span>1</span></a>
    """
    try:
        cur = driver.find_element(By.CSS_SELECTOR, "div.page01.js-tag a.page.on")
        # data-page 또는 표시 숫자
        dp = cur.get_attribute("data-page")
        if dp and dp.isdigit():
            return int(dp)
        # fallback: 내부 <span>의 표시 숫자
        return int(cur.find_element(By.TAG_NAME, "span").text.strip())
    except Exception:
        # on이 disabled일 수 있음 → disabled도 포함해서 재탐색
        try:
            cur = driver.find_element(By.CSS_SELECTOR, "div.page01.js-tag a.page.on.disabled")
            dp = cur.get_attribute("data-page")
            if dp and dp.isdigit():
                return int(dp)
            return int(cur.find_element(By.TAG_NAME, "span").text.strip())
        except Exception:
            return 1  # 기본값


def click_page_number(driver, page_num: int) -> bool:
    """
    숫자 페이지 클릭: a.page[data-page='{page_num}'] (btn 제외)
    """
    xp = f"//div[contains(@class,'page01') and contains(@class,'js-tag')]//a[contains(@class,'page') and not(contains(@class,'btn')) and @data-page='{page_num}']"
    els = driver.find_elements(By.XPATH, xp)
    for el in els:
        try:
            if el.is_displayed() and el.is_enabled():
                driver.execute_script("arguments[0].click();", el)
                return True
        except Exception:
            continue
    return False


def click_next_group(driver) -> bool:
    """
    다음 그룹(11, 21, ...) 이동 버튼 클릭
    DOM 예: <a href="#" data-page="11" class="page btn"><img alt="다음 페이지로 이동"></a>
    """
    xp_next = "//div[contains(@class,'page01') and contains(@class,'js-tag')]//a[contains(@class,'page') and contains(@class,'btn')][.//img[contains(@alt,'다음 페이지') or contains(@alt,'다음')]]"
    els = driver.find_elements(By.XPATH, xp_next)
    for el in els:
        try:
            if el.is_displayed() and el.is_enabled():
                driver.execute_script("arguments[0].click();", el)
                return True
        except Exception:
            continue
    return False


def crawl_category(driver, label: str, result_map: OrderedDict):
    """
    특정 간편분류 라벨(ㄱ~기타) 처리:
    - 탭 클릭
    - 페이지 1부터 시작해 숫자 페이지를 순차 클릭
    - 그룹 끝이면 '다음 페이지로 이동' 버튼으로 다음 그룹 진입
    - 더 이상 다음으로 갈 수 없을 때 종료
    """
    # 탭 클릭
    prev_first = get_first_term_text(driver)
    clicked = click_category(driver, label)
    if clicked:
        try:
            wait_after_navigation(driver, prev_first_term=prev_first)
        except TimeoutException:
            pass  # 결과 0개인 분류일 가능성

    # 페이지 루프
    visited = set()
    while True:
        # 현재 페이지 번호
        cur = get_current_page_number(driver)
        if cur in visited:
            break
        visited.add(cur)

        # 현재 페이지 수확
        items = collect_current_page_items(driver)
        for term, desc in items:
            if term not in result_map:
                result_map[term] = desc

        # 다음 페이지로 이동 시도
        next_page = cur + 1
        prev_first = get_first_term_text(driver)

        moved = click_page_number(driver, next_page)
        if moved:
            try:
                wait_after_navigation(driver, prev_first_term=prev_first)
            except TimeoutException:
                # 페이지 이동 실패 시 다음 그룹 시도
                pass
            continue

        # 숫자 페이지가 없으면, 다음 그룹 버튼 시도
        moved_group = click_next_group(driver)
        if moved_group:
            try:
                wait_after_navigation(driver, prev_first_term=prev_first)
            except TimeoutException:
                pass
            # 다음 그룹 진입 후, 바로 next_page(=cur+1) 숫자 클릭 재시도
            moved2 = click_page_number(driver, next_page)
            if moved2:
                try:
                    wait_after_navigation(driver, prev_first_term=prev_first)
                except TimeoutException:
                    pass
                continue

        # 더 이상 이동 불가 → 종료
        break

    print(f"[{label}] 누적 수집: {len(result_map)}")


def save_results(records):
    # JSON (UTF-8)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # CSV (UTF-8-SIG) — 엑셀 한글 호환
    fields = ["id","term","description","source","collected_date"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)


def main(headless=True):
    driver = make_driver(headless=headless)
    driver.get(BASE)
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(0.3)

    all_map = OrderedDict()
    for label in CATS:
        try:
            crawl_category(driver, label, all_map)
        except Exception as e:
            print(f"[WARN] 분류 {label} 처리 중 예외: {e}")

    driver.quit()

    # 레코드화
    records = []
    for i, (term, desc) in enumerate(all_map.items(), start=1):
        if not term or not desc:
            continue
        records.append(OrderedDict([
            ("id", i),
            ("term", term),
            ("description", desc),
            ("source", "DB생명"),
            ("collected_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]))

    print(f"최종 고유 용어 수: {len(records)} 개")
    save_results(records)


if __name__ == "__main__":
    # headless=False 로 바꾸면 브라우저 창이 보입니다.
    main(headless=True)
