# scrape_samsungfire_pc_tab_only.py
# Python 3.10+
import time, json, csv
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://direct.samsungfire.com/claim/PP040401_001.html"
TAB_TEXT_TARGET = "차 vs. 기타"  # 여기만 추출 (원하면 "차 vs. 차", "차 vs. 기타"로 바꿔 실행)

OUT_JSONL = Path("samsungfire_claim_cases_pc_tab.jsonl")
OUT_CSV   = Path("samsungfire_claim_cases_pc_tab.csv")

def setup_driver(headless=True):
    opt = Options()
    if headless:
        opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1440,1000")
    return webdriver.Chrome(options=opt)

def click(el, driver):
    driver.execute_script("arguments[0].click();", el)

def get_tab_button(driver, target_text):
    # 탭 버튼 안 <i>의 텍스트가 "차 vs. 사람" 인 버튼을 찾음
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.ui-tab-btn[role='tab']")
    for b in buttons:
        try:
            i = b.find_element(By.TAG_NAME, "i")
            if i.text.strip() == target_text:
                return b
        except Exception:
            continue
    return None

def ensure_panel_visible(driver, panel_id):
    # 해당 패널이 로딩/가시화될 때까지 대기
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, panel_id))
    )
    time.sleep(0.4)

def try_load_more_in_panel(panel_el, driver):
    # 패널 내부의 더보기/다음 버튼을 반복 클릭
    while True:
        # 더보기/다음 후보 셀렉터
        more_selectors = [
            "button.more", "a.more",
            "button.ui-more", "a.ui-more",
            "a.next", "button.next",
            "button[aria-label*='더보기']", "a[aria-label*='더보기']",
        ]
        load_more = None
        for sel in more_selectors:
            try:
                cand = panel_el.find_element(By.CSS_SELECTOR, sel)
                if cand.is_displayed() and cand.is_enabled():
                    load_more = cand
                    break
            except Exception:
                continue

        if not load_more:
            break
        # 클릭 후 내용 추가 로딩 대기
        click(load_more, driver)
        time.sleep(0.7)

def collect_pairs_from_panel(panel_el, driver):
    # 패널 내부에서 dl.info 각각과 직전 num을 페어링
    items = []
    dls = panel_el.find_elements(By.CSS_SELECTOR, "dl.info")
    for dl in dls:
        # 제목과 본문
        title = ""
        body  = ""
        try:
            title = dl.find_element(By.TAG_NAME, "dt").text.strip()
        except Exception:
            pass
        try:
            body = dl.find_element(By.TAG_NAME, "dd").text.strip()
        except Exception:
            pass
        # 번호: 직전 형제들의 .num 탐색
        num_text = ""
        try:
            # JS로 previousElementSibling 접근
            num_text = driver.execute_script("""
                const dl = arguments[0];
                let s = dl.previousElementSibling;
                while (s) {
                    if (s.classList && s.classList.contains('num')) return s.textContent.trim();
                    s = s.previousElementSibling;
                }
                return '';
            """, dl)
        except Exception:
            pass

        if title or body:
            items.append({
                "category": TAB_TEXT_TARGET,
                "num": num_text,
                "title": title,
                "body": body
            })
    return items

def main():
    drv = setup_driver(headless=True)
    try:
        drv.get(URL)
        WebDriverWait(drv, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(0.8)

        tab_btn = get_tab_button(drv, TAB_TEXT_TARGET)
        if not tab_btn:
            raise RuntimeError(f"탭 버튼을 찾지 못했습니다: {TAB_TEXT_TARGET}")

        # 탭 클릭
        click(tab_btn, drv)
        time.sleep(0.5)

        # 탭 버튼의 aria-controls 로 패널 ID 확보
        panel_id = tab_btn.get_attribute("aria-controls")
        if not panel_id:
            raise RuntimeError("aria-controls 없음: 패널 ID 확인 불가")

        ensure_panel_visible(drv, panel_id)
        panel_el = drv.find_element(By.ID, panel_id)

        # 패널 내 ‘더보기/다음’ 등을 끝까지 클릭
        try_load_more_in_panel(panel_el, drv)

        # 최종 수집
        rows = collect_pairs_from_panel(panel_el, drv)

        # 저장
        with OUT_JSONL.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["category","num","title","body"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"[DONE] {len(rows)}건 저장")
        print(f" - JSONL: {OUT_JSONL.resolve()}")
        print(f" - CSV  : {OUT_CSV.resolve()}")

    finally:
        drv.quit()

if __name__ == "__main__":
    main()
