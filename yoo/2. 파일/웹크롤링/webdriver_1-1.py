# 보험용어사전 웹크롤링 - 완전판
# 보험협회빅데이터

import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
import os

class InsuranceDictionaryCrawler:
    def __init__(self):
        self.base_url = "https://bigin.kidi.or.kr:9443"
        self.dictionary_url = "https://bigin.kidi.or.kr:9443/user/nd00007.action"
        
        # 크롬 옵션 설정
        self.chrome_options = Options()
        # self.chrome_options.add_argument('--headless')  # 브라우저 창 안보이게 (주석 해제하면 숨김)
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # User-Agent 설정
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        self.driver = None
        self.terms_data = []
    
    def setup_driver(self):
        """셀레니움 드라이버 설정"""
        try:
            if WEBDRIVER_MANAGER_AVAILABLE:
                # ChromeDriver 자동 다운로드 및 설정
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
            else:
                # 기본 방식
                self.driver = webdriver.Chrome(options=self.chrome_options)
            
            print("✅ 크롬 드라이버 설정 완료")
            return True
        except Exception as e:
            print(f"❌ 드라이버 설정 실패: {e}")
            print("ChromeDriver가 설치되어 있는지 확인하세요!")
            return False
    
    def scroll_and_load_all_terms(self):
        """페이지 스크롤하면서 모든 용어 로드"""
        try:
            self.driver.get(self.dictionary_url)
            print("페이지 로딩 중...")
            time.sleep(3)
            
            # 전체 버튼 클릭 (이미 선택되어 있을 수 있음)
            try:
                all_button = self.driver.find_element(By.XPATH, "//button[contains(text(), '전체')]")
                all_button.click()
                time.sleep(2)
                print("✅ 전체 버튼 클릭 완료")
            except:
                print("전체 버튼이 이미 선택되어 있거나 찾을 수 없음")
            
            # 스크롤하면서 모든 항목 로드
            print("스크롤 시작...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            
            while True:
                # 페이지 맨 아래로 스크롤
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 로딩 대기
                
                # 새로운 높이 확인
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_count += 1
                
                # 현재 로드된 항목 수 확인
                items = self.driver.find_elements(By.CSS_SELECTOR, "ol.bot li")
                print(f"스크롤 {scroll_count}회 - 현재 로드된 항목: {len(items)}개")
                
                # 더 이상 스크롤할 내용이 없으면 종료
                if new_height == last_height:
                    print("더 이상 로드할 항목이 없습니다.")
                    break
                    
                last_height = new_height
                
                # 안전장치: 너무 많이 스크롤하면 중단
                if scroll_count > 50:
                    print("⚠️ 스크롤 횟수가 너무 많습니다. 중단합니다.")
                    break
            
            return True
            
        except Exception as e:
            print(f"❌ 스크롤 로딩 실패: {e}")
            return False
    
    def extract_all_terms(self):
        """모든 용어 추출"""
        try:
            # 모든 용어 항목 찾기
            term_items = self.driver.find_elements(By.CSS_SELECTOR, "ol.bot li")
            print(f"총 {len(term_items)}개의 용어 발견")
            
            for i, item in enumerate(term_items):
                try:
                    # 용어명 추출
                    term_element = item.find_element(By.CSS_SELECTOR, "strong.word")
                    term = term_element.text.strip()
                    
                    # 설명 추출 - display:none 상태에서도 텍스트 가져오기
                    description = ""
                    try:
                        # 숨겨진 div에서 설명 추출
                        desc_div = item.find_element(By.CSS_SELECTOR, "div[id^='Desc']")
                        desc_p = desc_div.find_element(By.CSS_SELECTOR, "p.desc_text")
                        
                        # JavaScript로 숨겨진 텍스트 가져오기
                        description = self.driver.execute_script("return arguments[0].textContent;", desc_p).strip()
                        
                        # <br> 태그 제거 및 정리
                        description = description.replace('\n', ' ').replace('\r', ' ')
                        description = ' '.join(description.split())  # 여러 공백을 하나로
                        
                    except Exception as desc_error:
                        print(f"설명 추출 실패 for {term}: {desc_error}")
                        # 폴백: 전체 li에서 용어명 제외한 텍스트
                        full_text = item.get_attribute('textContent').strip()
                        if term in full_text:
                            description = full_text.replace(term, "").strip()
                    
                    # 빈 설명 체크
                    if not description or description == "":
                        print(f"⚠️ {term}: 설명이 비어있음")
                        description = "설명 없음"
                    
                    # 데이터 저장
                    term_data = {
                        'id': i + 1,
                        'term': term,
                        'description': description,
                        'source': 'KIDI_BIGIN',
                        'collected_date': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.terms_data.append(term_data)
                    
                    # 처음 5개는 상세 출력
                    if i < 5:
                        print(f"{i+1}. 용어: {term}")
                        print(f"   설명: {description[:100]}...")
                        print()
                    
                    # 진행상황 출력
                    elif (i + 1) % 50 == 0:
                        print(f"진행률: {i + 1}/{len(term_items)} ({((i + 1)/len(term_items)*100):.1f}%)")
                    
                except Exception as e:
                    print(f"⚠️ {i+1}번째 항목 처리 중 오류: {e}")
                    continue
            
            print(f"✅ 총 {len(self.terms_data)}개 용어 추출 완료")
            return True
            
        except Exception as e:
            print(f"❌ 용어 추출 실패: {e}")
            return False
    
    def save_to_csv(self, filename="insurance_terms.csv"):
        """CSV 파일로 저장"""
        try:
            if not self.terms_data:
                print("저장할 데이터가 없습니다.")
                return False
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'term', 'description', 'source', 'collected_date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for term in self.terms_data:
                    writer.writerow(term)
            
            print(f"✅ CSV 파일 저장 완료: {filename}")
            print(f"파일 위치: {os.path.abspath(filename)}")
            return True
            
        except Exception as e:
            print(f"❌ CSV 저장 실패: {e}")
            return False
    
    def save_to_json(self, filename="insurance_terms.json"):
        """JSON 파일로 저장 (백업용)"""
        try:
            if not self.terms_data:
                print("저장할 데이터가 없습니다.")
                return False
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(self.terms_data, jsonfile, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON 파일 저장 완료: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ JSON 저장 실패: {e}")
            return False
    
    def print_sample_data(self, count=5):
        """샘플 데이터 출력"""
        print(f"\n=== 샘플 데이터 (처음 {count}개) ===")
        for i, term in enumerate(self.terms_data[:count]):
            print(f"{i+1}. {term['term']}")
            print(f"   설명: {term['description'][:100]}...")
            print(f"   수집일시: {term['collected_date']}")
            print()
    
    def run_full_crawling(self):
        """전체 크롤링 실행"""
        print("🚀 보험용어사전 크롤링 시작...")
        
        # 1단계: 드라이버 설정
        if not self.setup_driver():
            return False
        
        try:
            # 2단계: 스크롤하며 모든 용어 로드
            if not self.scroll_and_load_all_terms():
                return False
            
            # 3단계: 용어 추출
            if not self.extract_all_terms():
                return False
            
            # 4단계: 샘플 데이터 확인
            self.print_sample_data()
            
            # 5단계: 파일 저장
            self.save_to_csv()
            self.save_to_json()
            
            print(f"🎉 크롤링 완료! 총 {len(self.terms_data)}개 용어 수집")
            return True
            
        finally:
            # 드라이버 종료
            if self.driver:
                self.driver.quit()
                print("브라우저 종료")

# 실행 코드
if __name__ == "__main__":
    crawler = InsuranceDictionaryCrawler()
    crawler.run_full_crawling()