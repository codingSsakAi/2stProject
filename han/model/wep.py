import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os

class AccidentCrawler:
    def __init__(self):
        self.driver = None
        self.data_file = "accident_data_complete.json"
        self.progress_file = "progress.json"
        self.base_url = "https://www.samsungfire.com/v2/html/claim/05/C_050_010_001.html"
        
    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"completed_tabs": [], "completed_items": []}
    
    def save_progress(self, progress):
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    def load_existing_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_data(self, data):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def safe_get_text(self, selector, parent=None):
        try:
            if parent:
                element = parent.find_element(By.CSS_SELECTOR, selector)
            else:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except:
            return ""

    def get_all_texts(self, selector, parent=None):
        try:
            if parent:
                elements = parent.find_elements(By.CSS_SELECTOR, selector)
            else:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            return [elem.text.strip() for elem in elements if elem.text.strip()]
        except:
            return []

    def extract_case_data(self):
        """상세 페이지에서 데이터 추출"""
        data = {}
        
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".reward_box"))
            )
            
            # case_visual 영역 정보
            data['case_visual'] = {
                'title': self.safe_get_text(".case_visual .txt strong"),
                'description': self.safe_get_text(".case_visual .txt p")
            }
            
            # 기본 정보
            data['title'] = self.safe_get_text(".reward_box .title-lg .txt")
            data['situation'] = self.safe_get_text(".reward_box .fc-gray1.fz-lg")
            data['situation_highlight'] = self.safe_get_text(".situa_txt .underline")
            
            # 섹션별 데이터
            data['sections'] = {}
            sections = self.driver.find_elements(By.CSS_SELECTOR, ".reward_box .group")
            
            for i, section in enumerate(sections):
                section_data = {}
                icon_elem = section.find_elements(By.CSS_SELECTOR, ".tit.icon")
                if icon_elem:
                    icon_classes = icon_elem[0].get_attribute("class")
                    
                    if "case1" in icon_classes:
                        section_data['type'] = '과실비율'
                        section_data['title'] = self.safe_get_text(".title-sm .txt", section)
                        section_data['main_ratio'] = self.safe_get_text(".reward_txt_black", section)
                        section_data['details'] = self.get_all_texts(".reward_txt", section)
                        section_data['additional_cases'] = self.get_all_texts(".module-box p", section)
                    
                    elif "case2" in icon_classes:
                        section_data['type'] = 'key point'
                        section_data['title'] = self.safe_get_text(".title-sm .txt", section)
                        section_data['subtitles'] = self.get_all_texts(".reward_txt_black", section)
                        section_data['details'] = self.get_all_texts(".reward_txt", section)
                    
                    elif "case3" in icon_classes:
                        section_data['type'] = '꿀팁'
                        section_data['title'] = self.safe_get_text(".title-sm .txt", section)
                        section_data['steps'] = self.get_all_texts(".reward_step_list li", section)
                        section_data['subtitles'] = self.get_all_texts(".reward_txt_black", section)
                        section_data['details'] = self.get_all_texts(".reward_txt", section)
                    
                    elif "case4" in icon_classes:
                        section_data['type'] = 'Q&A'
                        section_data['title'] = self.safe_get_text(".title-sm .txt", section)
                        all_blacks = self.get_all_texts(".reward_txt_black", section)
                        section_data['question'] = all_blacks[0] if all_blacks else ""
                        section_data['answer_title'] = self.safe_get_text(".reward_txt_black.fw-normal", section)
                        section_data['answer_details'] = self.get_all_texts(".reward_txt", section)
                
                if section_data:
                    data['sections'][f'section_{i}'] = section_data
            
            try:
                data['full_content'] = self.driver.find_element(By.CSS_SELECTOR, ".reward_box").text
            except:
                data['full_content'] = ""
            
            return data

        except Exception as e:
            print(f"데이터 추출 중 오류: {e}")
            return None

    def get_tab_cases_only(self, target_tab_name):
        """현재 탭에 해당하는 사례만 필터링"""
        try:
            # 모든 .txt 요소 찾기
            all_txt_elements = self.driver.find_elements(By.CSS_SELECTOR, ".txt")
            
            # 해당 탭에 속하는 사례만 필터링
            tab_cases = []
            for txt_elem in all_txt_elements:
                try:
                    span_elem = txt_elem.find_element(By.CSS_SELECTOR, "span")
                    if span_elem.text.strip() == target_tab_name:
                        tab_cases.append(txt_elem)
                except:
                    continue
            
            print(f"'{target_tab_name}' 탭에서 {len(tab_cases)}개 사례 발견")
            return tab_cases
            
        except Exception as e:
            print(f"탭별 사례 필터링 오류: {e}")
            return []

    def crawl_tab(self, tab_name, tab_selector):
        print(f"\n=== [{tab_name}] 크롤링 시작 ===")
        
        # 메인 페이지 이동
        self.driver.get(self.base_url)
        time.sleep(3)
        
        # 탭 클릭
        try:
            tab_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, tab_selector))
            )
            self.driver.execute_script("arguments[0].click();", tab_element)
            time.sleep(3)
            print(f"[{tab_name}] 탭 활성화 완료")
        except Exception as e:
            print(f"[{tab_name}] 탭 클릭 실패: {e}")
            return
        
        # 해당 탭의 사례만 가져오기
        case_elements = self.get_tab_cases_only(tab_name)
        
        if not case_elements:
            print(f"[{tab_name}] 사례를 찾을 수 없습니다.")
            return
        
        progress = self.load_progress()
        
        # 각 사례 처리
        for i in range(len(case_elements)):
            case_id = f"{tab_name}_{i}"
            
            if case_id in progress.get("completed_items", []):
                print(f"건너뛰기: {case_id}")
                continue
            
            print(f"\n[{i+1}/{len(case_elements)}] 처리 중: {case_id}")
            
            try:
                # 매번 새로 페이지 로드
                self.driver.get(self.base_url)
                time.sleep(2)
                
                # 탭 재클릭
                tab_element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, tab_selector))
                )
                self.driver.execute_script("arguments[0].click();", tab_element)
                time.sleep(2)
                
                # 해당 탭의 사례 다시 찾기
                current_cases = self.get_tab_cases_only(tab_name)
                
                if i >= len(current_cases):
                    print(f"인덱스 {i} 초과, 건너뛰기")
                    continue
                
                case_elem = current_cases[i]
                
                # 사례 클릭
                self.driver.execute_script("arguments[0].click();", case_elem)
                time.sleep(4)
                
                # 데이터 추출
                case_data = self.extract_case_data()
                if case_data:
                    case_data['category'] = tab_name
                    case_data['case_id'] = case_id
                    
                    # 저장
                    existing_data = self.load_existing_data()
                    existing_data.append(case_data)
                    self.save_data(existing_data)
                    
                    # 진행상황 업데이트
                    progress["completed_items"].append(case_id)
                    self.save_progress(progress)
                    
                    print(f"✓ 저장 완료: {case_id}")
                else:
                    print(f"✗ 데이터 추출 실패: {case_id}")

            except Exception as e:
                print(f"✗ 오류 발생 {case_id}: {e}")
                continue
        
        # 탭 완료 표시
        progress["completed_tabs"].append(tab_name)
        self.save_progress(progress)
        print(f"\n=== [{tab_name}] 완료 ===")

    def run(self):
        try:
            print("🚀 크롤링 시작!")
            self.setup_driver()
            
            progress = self.load_progress()
            
            tabs = [
                ("차 vs. 차", ".ui-tab-btn:nth-child(1)"),
                ("차 vs. 사람", ".ui-tab-btn:nth-child(2)"), 
                ("차 vs. 기타", ".ui-tab-btn:nth-child(3)")
            ]
            
            for tab_name, tab_selector in tabs:
                if tab_name not in progress.get("completed_tabs", []):
                    self.crawl_tab(tab_name, tab_selector)
                else:
                    print(f"✓ {tab_name} 이미 완료됨")
            
            print("\n🎉 전체 크롤링 완료!")
            
        except Exception as e:
            print(f"전체 크롤링 오류: {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    crawler = AccidentCrawler()
    crawler.run()