# -*- coding: utf-8 -*-
"""
KNIA 보험용어 사전(https://www.knia.or.kr/howtouse/dictionary) 전체 수집 스크립트
- Selenium 기반 동적 로딩 대응
- 탭(가나다/알파벳/숫자/기타) 전부 순회
- 더보기(버튼/무한스크롤) 로딩 루프
- 항목 파싱: DL(dt/dd) → 카드(li) → 헤더(h3/h4) 세 단계 시도
- 저장: JSON(UTF-8) + CSV(UTF-8-SIG, 엑셀 호환)
"""

import os
import re
import csv
import json
import time
import math
from datetime import datetime
from collections import OrderedDict

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, StaleElementReferenceException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL = "https://www.knia.or.kr/howtouse/dictionary"

# 출력 파일명
OUT_JSON = "knia_insurance_terms_full.json"
OUT_CSV  = "knia_insurance_terms_full.csv"

# 로딩/대기 기본값
WAIT_SEC = 10
SCROLL_PAUSE = 0.6
STALL_LIMIT = 4  # 연속 증가 없음 허용 횟수
MAX_SCROLL = 200  # 안전 상한


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def norm_term(s: str) -> str:
    s = clean_text(s)
    # 제목 앞 장식 문자 제거
    s = re.sub(r'^[#\-\*\s·•\u00B7]+', '', s)
    # 끝 장식 제거
    s = re.sub(r'[\-\*\s·•\u00B7]+$', '', s)
    return s.strip()


def make_driver(headless=True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--window-size=1400,2000")
    opts.add_argument("--disable-dev-shm-usage")
    # 최신 Selenium(4.6+)은 드라이버 자동 관리 지원
    driver = webdriver.Chrome(options=opts, service=Service())
    driver.set_page_load_timeout(30)
    return driver


def get_total_count_text(page_text: str) -> int:
    # 페이지 전체 텍스트에서 "총 n 건" 패턴 우선 탐지
    m = re.search(r"총\s*([0-9,]+)\s*건", page_text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except:
            pass
    # 예비: "(801건)" 같은 표기
    m = re.search(r"\(([0-9,]+)\s*건\)", page_text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except:
            pass
    return -1


def wait_dom_settled(driver):
    # 간단한 로딩 안정화: 스크립트 큐가 비는 것을 약간 기다림
    time.sleep(0.3)


def click_if_present(driver, by, selector) -> bool:
    try:
        elem = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, selector)))
        driver.execute_script("arguments[0].click();", elem)
        return True
    except Exception:
        return False


def try_click_more(driver) -> bool:
    # 더보기 버튼 후보들(텍스트/클래스)
    candidates = [
        ("css", "button.more"),
        ("css", ".btn-more"),
        ("css", ".btn_more"),
        ("css", "a.more"),
        ("css", "a.btn-more"),
        ("xpath", "//button[contains(., '더보기') or contains(., '더 보기')]"),
        ("xpath", "//a[contains(., '더보기') or contains(., '더 보기')]"),
    ]
    for how, sel in candidates:
        try:
            if how == "css":
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
            else:
                elems = driver.find_elements(By.XPATH, sel)
            for e in elems:
                if e.is_displayed() and e.is_enabled():
                    driver.execute_script("arguments[0].click();", e)
                    return True
        except Exception:
            continue
    return False


def smart_scroll(driver, last_height=None):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE)
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height


def collect_cards_webelements(driver):
    """
    사전 항목(li/카드) WebElement 후보들을 최대 매칭 셀렉터로 추출
    """
    selector_groups = [
        ".dictionary-list li",
        ".result-list li",
        ".board-list li",
        ".list-wrap li",
        "ul.list li",
        "ul > li.item",
        ".item-list > li",
    ]
    max_list = []
    for sel in selector_groups:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(elems) > len(max_list):
                max_list = elems
        except Exception:
            pass
    return max_list


def parse_items_from_cards(cards):
    """
    li/카드 요소에서 제목/설명 뽑기
    """
    items = []
    for li in cards:
        try:
            title = ""
            desc = ""

            # 제목 후보
            title_cands = [
                ".tit", ".subject", "h4", "h3", "strong", ".title",
            ]
            for ts in title_cands:
                try:
                    t = li.find_element(By.CSS_SELECTOR, ts).text
                    if t and len(clean_text(t)) > 0:
                        title = clean_text(t)
                        break
                except Exception:
                    continue

            # 설명 후보: li 내부에서 제목 이외 텍스트
            # 우선 순위: .desc / p / div.text
            desc_cands = [".desc", ".txt", ".text"]
            for ds in desc_cands:
                try:
                    d = li.find_element(By.CSS_SELECTOR, ds).text
                    if d and len(clean_text(d)) > 0:
                        desc = clean_text(d)
                        break
                except Exception:
                    continue

            if not desc:
                # 모든 하위 텍스트 긁어 모으되, 제목 텍스트는 제거
                full = li.text
                if title:
                    full = full.replace(title, " ")
                desc = clean_text(full)

            title = norm_term(title)
            if not title or len(desc) < 20:
                continue

            items.append((title, desc))
        except StaleElementReferenceException:
            continue
        except Exception:
            continue
    return items


def parse_items_from_dl(html):
    """
    DL(dt/dd) 구조에서 추출
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        # dt/dd가 1:1이거나 근접한 경우만 처리
        if not dts or not dds:
            continue
        # 단순 매칭
        n = min(len(dts), len(dds))
        for i in range(n):
            t = norm_term(dts[i].get_text(" ", strip=True))
            d = clean_text(dds[i].get_text(" ", strip=True))
            if t and len(d) >= 20:
                items.append((t, d))
    return items


def parse_items_from_headers(html):
    """
    헤더(h3/h4) → 다음 헤더 전까지 설명 합치기
    """
    soup = BeautifulSoup(html, "html.parser")
    hs = soup.find_all(["h3", "h4"])
    items = []
    for i, h in enumerate(hs):
        t = norm_term(h.get_text(" ", strip=True))
        if not t or len(t) > 150:
            continue
        # 금칙어(페이지 공통 헤더 등) 배제
        if any(x in t for x in ["보험용어", "검색", "HOME"]):
            continue
        # 다음 헤더 전까지 텍스트
        desc_chunks = []
        sib = h.find_next_sibling()
        while sib and sib.name not in ("h3", "h4"):
            txt = sib.get_text(" ", strip=True)
            if txt:
                desc_chunks.append(txt)
            sib = sib.find_next_sibling()
        d = clean_text(" ".join(desc_chunks))
        if len(d) >= 20:
            items.append((t, d))
    return items


def harvest_current_page(driver):
    """
    현재 화면에서 항목 추출을 시도(DL → CARD → HEADER 순)
    """
    html = driver.page_source

    # 1) DL 시도
    dl_items = parse_items_from_dl(html)
    if len(dl_items) >= 50:
        return dl_items

    # 2) 카드(li) 시도
    cards = collect_cards_webelements(driver)
    card_items = parse_items_from_cards(cards)
    if len(card_items) >= 50:
        return card_items

    # 3) 헤더 시도
    header_items = parse_items_from_headers(html)
    return header_items


def load_all_for_tab(driver, expected_total=-1):
    """
    이 탭(또는 전체)에서 '더보기/스크롤'을 반복해서 끝까지 펼치기
    - expected_total: 탭별 총 건수(없으면 -1)
    """
    stall = 0
    last_count = -1
    last_height = None
    scrolls = 0

    while True:
        cards = collect_cards_webelements(driver)
        cur = len(cards)

        # expected_total에 도달하면 종료
        if expected_total > 0 and cur >= expected_total:
            break

        # '더보기' 우선 클릭
        clicked = try_click_more(driver)
        wait_dom_settled(driver)

        # 더보기 없으면 스크롤
        if not clicked:
            new_height = smart_scroll(driver, last_height)
            last_height = new_height
            scrolls += 1

        # 증가 감시
        cards_after = collect_cards_webelements(driver)
        cur_after = len(cards_after)
        if cur_after <= cur:
            stall += 1
        else:
            stall = 0

        # 안전 종료 조건
        if stall >= STALL_LIMIT or scrolls >= MAX_SCROLL:
            break


def iter_tabs(driver):
    """
    탭(가나다/알파벳/숫자/기타)을 모두 찾아 순회하는 제너레이터
    - 탭 요소가 없다면 빈 리스트 반환(= '전체'만 있는 경우)
    """
    # 탭 후보 셀렉터
    tab_selectors = [
        ".index-tabs a", ".index-tabs button",
        ".alphabet a", ".alphabet button",
        ".filter a", ".filter button",
        ".tab a", ".tab button",
        "[role='tab']", ".tabs a", ".tabs button",
    ]
    tabs = []
    seen = set()

    for sel in tab_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                try:
                    key = (e.tag_name, e.text.strip(), e.get_attribute("href") or "")
                except Exception:
                    key = (e.tag_name, "", "")
                if key in seen:
                    continue
                seen.add(key)
                # 보이는 탭만 채택
                try:
                    if e.is_displayed():
                        tabs.append(e)
                except Exception:
                    continue
        except Exception:
            continue

    return tabs


def get_expected_total_for_current(driver) -> int:
    # 현재 페이지 영역에서 총 건수 추출
    text = driver.find_element(By.TAG_NAME, "body").text
    return get_total_count_text(text)


def crawl_knia_dictionary(headless=True):
    driver = make_driver(headless=headless)
    driver.get(URL)
    wait_dom_settled(driver)

    all_items_map = OrderedDict()  # term -> description
    total_expected_overall = get_expected_total_for_current(driver)

    tabs = iter_tabs(driver)

    if not tabs:
        # 탭이 없으면 전체에서 끝까지 펼친 뒤 수확
        load_all_for_tab(driver, expected_total=total_expected_overall)
        items = harvest_current_page(driver)
        for t, d in items:
            if t not in all_items_map:
                all_items_map[t] = d
    else:
        # 탭이 있으면 전부 순회
        for idx, tab in enumerate(tabs, 1):
            try:
                driver.execute_script("arguments[0].click();", tab)
            except Exception:
                try:
                    ActionChains(driver).move_to_element(tab).click().perform()
                except Exception:
                    continue
            wait_dom_settled(driver)

            # 탭별 기대치(없으면 -1)
            expected = get_expected_total_for_current(driver)
            load_all_for_tab(driver, expected_total=expected)
            items = harvest_current_page(driver)
            for t, d in items:
                if t not in all_items_map:
                    all_items_map[t] = d

    driver.quit()

    # 최소 품질 필터링
    records = []
    for i, (term, desc) in enumerate(all_items_map.items(), 1):
        if not term or not desc or len(desc) < 20:
            continue
        if len(term) > 200:
            continue
        if re.search(r"[.!?]\s", term):
            # 문장처럼 보이는 제목은 제외
            continue
        records.append(OrderedDict([
            ("id", i),
            ("term", term),
            ("description", desc),
            ("source", "KNIA"),
            ("collected_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]))

    # 기대치와 비교(정보용)
    scraped = len(records)
    print(f"expected overall: {total_expected_overall}, scraped unique: {scraped}")

    # 저장(JSON UTF-8)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # 저장(CSV UTF-8-SIG: 엑셀 한글 호환)
    fieldnames = ["id", "term", "description", "source", "collected_date"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return records, total_expected_overall


if __name__ == "__main__":
    # headless=False 로 바꾸면 크롬 창 보이게 실행
    crawl_knia_dictionary(headless=True)
