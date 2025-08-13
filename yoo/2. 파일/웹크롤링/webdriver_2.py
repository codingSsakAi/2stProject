# 한국손해보험협회 보험용어사전 웹크롤링 - 최종 완성판

import requests
from bs4 import BeautifulSoup
import time
import json
import csv
import re
import os

class KNIAInsuranceDictionaryCrawler:
    def __init__(self):
        self.dictionary_url = "https://www.knia.or.kr/howtouse/dictionary"
        self.terms_data = []
    
    def extract_terms_from_text(self):
        """HTML 텍스트에서 직접 용어와 설명 추출"""
        try:
            # 웹페이지 요청
            response = requests.get(self.dictionary_url, timeout=10)
            response.encoding = 'utf-8'
            
            print("페이지 다운로드 완료")
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 전체 텍스트 추출
            full_text = soup.get_text()
            
            # "용어설명" 다음 부분부터 추출
            text_lines = full_text.split('\n')
            
            # 용어설명 섹션 찾기
            explanation_start = -1
            for i, line in enumerate(text_lines):
                if '용어설명' in line:
                    explanation_start = i + 1
                    break
            
            if explanation_start == -1:
                print("❌ 용어설명 섹션을 찾을 수 없습니다.")
                return False
            
            print(f"용어설명 섹션 시작: {explanation_start}번째 줄")
            
            # 용어설명 이후의 모든 텍스트 결합
            explanation_text = '\n'.join(text_lines[explanation_start:])
            
            # 알려진 용어들을 미리 정의 (웹에서 확인한 첫 몇 개)
            known_terms = [
                "가산연금",
                "가스배상책임보험", 
                "가입경력선정인",
                "가입자특성요율",
                "가재도구",
                "가정간호비",
                "가족상해보험(家族傷害保險)",
                "가족운전자",
                "가족운전자 한정 운전특약"
            ]
            
            # 정규식 패턴으로 용어-설명 매칭
            print("정규식으로 용어-설명 매칭 중...")
            
            # 패턴 1: 한글 용어 + 설명 (괄호, 영어 포함 가능)
            pattern = r'([가-힣]+(?:\([^)]*\))?(?:\s*\[[^\]]*\])?)\s*\n([가-힣].*?)(?=\n[가-힣]+(?:\([^)]*\))?(?:\s*\[[^\]]*\])?\s*\n|$)'
            matches = re.findall(pattern, explanation_text, re.DOTALL)
            
            print(f"패턴 1로 {len(matches)}개 매칭 발견")
            
            if len(matches) < 100:
                # 패턴 2: 더 단순한 방식
                lines = explanation_text.split('\n')
                matches = []
                
                i = 0
                while i < len(lines) - 1:
                    line = lines[i].strip()
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    
                    # 용어로 보이는 줄 (한글, 괄호, 영어 포함)
                    if (re.match(r'^[가-힣]+', line) and 
                        len(line) < 100 and 
                        next_line and 
                        len(next_line) > 10):
                        
                        # 설명 수집 (여러 줄일 수 있음)
                        description_lines = [next_line]
                        j = i + 2
                        
                        while j < len(lines):
                            next_next_line = lines[j].strip()
                            # 다음 용어가 시작되기 전까지
                            if re.match(r'^[가-힣]+', next_next_line) and len(next_next_line) < 100:
                                break
                            if next_next_line:
                                description_lines.append(next_next_line)
                            j += 1
                        
                        description = ' '.join(description_lines).strip()
                        if description:
                            matches.append((line, description))
                        
                        i = j - 1
                    
                    i += 1
                
                print(f"패턴 2로 {len(matches)}개 매칭 발견")
            
            # 데이터 정리 및 저장
            print("데이터 정리 중...")
            
            for i, (term, description) in enumerate(matches):
                term = term.strip()
                description = description.strip()
                
                # 정리 작업
                term = re.sub(r'\s+', ' ', term)
                description = re.sub(r'\s+', ' ', description)
                
                # 유효성 검사
                if (len(term) > 1 and 
                    len(term) < 100 and 
                    len(description) > 10 and
                    not any(skip in term for skip in ['총', '건', '검색', 'HOME'])):
                    
                    term_data = {
                        'id': len(self.terms_data) + 1,
                        'term': term,
                        'description': description,
                        'source': 'KNIA',
                        'collected_date': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.terms_data.append(term_data)
                    
                    # 처음 10개 출력
                    if len(self.terms_data) <= 10:
                        print(f"{len(self.terms_data)}. {term}: {description[:80]}...")
            
            print(f"✅ 총 {len(self.terms_data)}개 용어 추출 완료")
            return len(self.terms_data) > 0
            
        except Exception as e:
            print(f"❌ 텍스트 추출 실패: {e}")
            return False
    
    def save_to_csv(self, filename="knia_insurance_terms_final.csv"):
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
    
    def save_to_json(self, filename="knia_insurance_terms_final.json"):
        """JSON 파일로 저장"""
        try:
            if not self.terms_data:
                return False
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(self.terms_data, jsonfile, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON 파일 저장 완료: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ JSON 저장 실패: {e}")
            return False
    
    def print_summary(self):
        """수집 결과 요약"""
        if self.terms_data:
            print(f"\n📊 수집 결과 요약")
            print(f"총 용어 수: {len(self.terms_data)}개")
            print(f"출처: 한국손해보험협회")
            print(f"URL: {self.dictionary_url}")
            
            # 샘플 데이터 출력
            print(f"\n📝 샘플 데이터 (처음 5개)")
            for i, term in enumerate(self.terms_data[:5]):
                print(f"{i+1}. {term['term']}")
                print(f"   {term['description'][:100]}...")
                print()
    
    def run_crawling(self):
        """전체 크롤링 실행"""
        print("🚀 KNIA 보험용어사전 크롤링 시작...")
        print("방법: HTML 텍스트 직접 분석")
        
        # 텍스트에서 직접 추출
        if self.extract_terms_from_text():
            # 결과 출력
            self.print_summary()
            
            # 파일 저장
            self.save_to_csv()
            self.save_to_json()
            
            print(f"🎉 크롤링 완료! 총 {len(self.terms_data)}개 용어 수집")
            return True
        else:
            print("❌ 크롤링 실패")
            return False

# 실행 코드
if __name__ == "__main__":
    crawler = KNIAInsuranceDictionaryCrawler()
    success = crawler.run_crawling()
    
    if success:
        print("\n✅ 모든 작업 완료!")
        print(" 용어 데이터베이스가 준비되었습니다!")
    else:
        print("\n❌ 작업 실패")