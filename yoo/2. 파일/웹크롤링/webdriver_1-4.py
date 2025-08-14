# -*- coding: utf-8 -*-
"""
하나생명 보험용어 사전 크롤러
URL: https://www.hanalife.co.kr/cmn/insuranceCommonSense/hanaCommunityDefinition.do

구조 요약:
- 상단 자모(ㄱ~ㅎ): ul.han-list.clearfix > li > a[href^="javascript:fn_detail('X')"]
- 좌측 용어 목록:   div.clearfix.mb30.hanlist-wrap > div.flt-l > ul > li > a
- 우측 상세 패널:   div.board-view1.han-sub.flt-r.mt30 안의 #subject / #content

동작:
1) ㄱ~ㅎ 자모 전부 클릭
2) 자모별 좌측 목록의 모든 항목을 차례대로 클릭해 #subject/#content 스냅샷
3) JSON(UTF-8), CSV(UTF-8-SIG) 저장
"""

import re
import csv
import json
import time
from datetime import datetime
from collections import OrderedDict

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

BASE = "https://www.hanalife.co.kr/cmn/insuranceCommonSense/hanaCommunityDefinition.do"
OUT_JSON = "hanalife_insurance_terms.json"
OUT_CSV  = "hanalife_insurance_terms.csv"

WAIT = 10

# 한글 자모: ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ
JAMO = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]


def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--window-size=1400,2200")
    opts.add_argument("--disable-dev-shm-usage")
    # Selenium 4.6+ 드라이버 자동 관리
    driver = webdriver.Chrome(options=opts, service=Service())
    driver.set_page_load_timeout(30)
    return driver


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def wait_for_body(driver):
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def get_subject_text(driver) -> str:
    try:
        return clean_text(driver.find_element(By.CSS_SELECTOR, "#subject").text)
    except Exception:
        return ""


def get_content_text(driver) -> str:
    try:
        return clean_text(driver.find_element(By.CSS_SELECTOR, "#content").text)
    except Exception:
        return ""


def click_jamo(driver, label: str) -> bool:
    """
    상단 자모 클릭: ul.han-list.clearfix 에서 해당 라벨(anchor) 클릭
    a[href*="fn_detail('라벨')"] 또는 텍스트 매칭(span)로 탐색
    """
    # 1) href 패턴으로 우선 시도
    xp = f"//ul[contains(@class,'han-list') and contains(@class,'clearfix')]//a[contains(@href, \"fn_detail('{label}')\")]"
    els = driver.find_elements(By.XPATH, xp)
    if not els:
        # 2) 표시 텍스트(자모)로 보조
        xp2 = f"//ul[contains(@class,'han-list') and contains(@class,'clearfix')]//a[normalize-space(.)='{label}' or span[normalize-space(text())='{label}']]"
        els = driver.find_elements(By.XPATH, xp2)

    for el in els:
        try:
            if el.is_displayed() and el.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.1)
                driver.execute_script("arguments[0].click();", el)
                return True
        except Exception:
            continue
    return False


def wait_list_loaded(driver):
    """
    자모 클릭 후 좌측 목록이 채워질 때까지 대기
    컨테이너: div.clearfix.mb30.hanlist-wrap > div.flt-l > ul > li
    """
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.clearfix.mb30.hanlist-wrap div.flt-l ul li a")
        )
    )
    time.sleep(0.2)


def get_left_list_count(driver) -> int:
    try:
        return len(driver.find_elements(By.CSS_SELECTOR, "div.clearfix.mb30.hanlist-wrap div.flt-l ul li a"))
    except Exception:
        return 0


def click_left_item_by_index(driver, idx: int) -> str:
    """
    좌측 목록의 idx번째 항목 클릭.
    클릭 전/후 subject 텍스트 변화를 대기 신호로 사용.
    반환: 클릭 후 subject 텍스트
    """
    # 항상 최신 목록 재조회(스테일 방지)
    items = driver.find_elements(By.CSS_SELECTOR, "div.clearfix.mb30.hanlist-wrap div.flt-l ul li a")
    if idx < 0 or idx >= len(items):
        return ""

    el = items[idx]
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.05)

    prev_subj = get_subject_text(driver)

    # 클릭(일부 요소는 .click()이 막힐 수 있어 JS 클릭 병행)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)

    # subject 변화 대기
    def changed(d):
        try:
            now = clean_text(d.find_element(By.CSS_SELECTOR, "#subject").text)
            return now and now != prev_subj
        except Exception:
            return False

    try:
        WebDriverWait(driver, WAIT).until(changed)
    except TimeoutException:
        # 변화가 없더라도 첫 클릭에서 subject가 비어있던 경우를 고려해 소폭 대기
        time.sleep(0.3)

    return get_subject_text(driver)


def crawl_hanalife(headless=True):
    driver = make_driver(headless=headless)
    driver.get(BASE)
    wait_for_body(driver)
    time.sleep(0.3)

    results_map = OrderedDict()  # term -> description

    for label in JAMO:
        try:
            # 자모 클릭
            ok = click_jamo(driver, label)
            if not ok:
                print(f"[WARN] 자모 '{label}' 클릭 실패(건너뜀)")
                continue

            # 좌측 목록 로딩 대기
            try:
                wait_list_loaded(driver)
            except TimeoutException:
                print(f"[WARN] 자모 '{label}' 목록 로딩 실패(건너뜀)")
                continue

            # 목록 개수 확인
            total = get_left_list_count(driver)
            if total == 0:
                print(f"[INFO] 자모 '{label}' 항목 0개")
                continue

            # 목록 전체 순회
            for i in range(total):
                try:
                    subj_after = click_left_item_by_index(driver, i)
                    # 우측 패널에서 subject/content 읽기
                    subject = subj_after or get_subject_text(driver)
                    content = get_content_text(driver)

                    subject = clean_text(subject)
                    content = clean_text(content)

                    if subject and content:
                        if subject not in results_map:
                            results_map[subject] = content
                except StaleElementReferenceException:
                    # 재시도: 스테일 발생 시 약간 대기 후 재클릭
                    time.sleep(0.2)
                    try:
                        subj_after = click_left_item_by_index(driver, i)
                        subject = subj_after or get_subject_text(driver)
                        content = get_content_text(driver)
                        subject = clean_text(subject)
                        content = clean_text(content)
                        if subject and content and subject not in results_map:
                            results_map[subject] = content
                    except Exception:
                        continue
                except Exception as e:
                    print(f"[WARN] 자모 '{label}' 인덱스 {i} 처리 중 예외: {e}")
                    continue

            print(f"[{label}] 누적 수집: {len(results_map)}")
        except Exception as e:
            print(f"[WARN] 자모 '{label}' 처리 중 예외: {e}")

    driver.quit()

    # 레코드화
    records = []
    for i, (term, desc) in enumerate(results_map.items(), start=1):
        records.append({
            "id": i,
            "term": term,
            "description": desc,
            "source": "한화생명",
            "collected_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    # 저장(JSON UTF-8)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # 저장(CSV UTF-8-SIG)
    fields = ["id", "term", "description", "source", "collected_date"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)

    print(f"최종 고유 용어 수: {len(records)}")
    print(f"저장 파일: {OUT_JSON}, {OUT_CSV}")


if __name__ == "__main__":
    # headless=False 로 바꾸면 브라우저 창이 보입니다.
    crawl_hanalife(headless=True)
