# CSV 파일 단어 빈도 분석기
# 추출된 보험 데이터에서 가장 많이 나오는 단어들 분석

import pandas as pd
import json
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns

class WordFrequencyAnalyzer:
    """CSV 파일에서 단어 빈도 분석"""
    
    def __init__(self, csv_file_path):
        self.csv_file = csv_file_path
        self.df = None
        self.word_analysis = {}
        
    def load_csv(self):
        """CSV 파일 로드"""
        try:
            self.df = pd.read_csv(self.csv_file, encoding='utf-8-sig')
            print(f"✅ CSV 파일 로드 완료: {len(self.df)}개 상품")
            return True
        except Exception as e:
            print(f"❌ CSV 파일 로드 실패: {str(e)}")
            return False
    
    def analyze_word_frequency(self):
        """전체 단어 빈도 분석"""
        
        if self.df is None:
            print("❌ CSV 파일을 먼저 로드해주세요.")
            return
        
        print("\n📊 단어 빈도 분석 시작...")
        
        # 모든 텍스트 수집
        all_text = self._collect_all_text()
        
        # 단어 분석
        self.word_analysis = {
            'korean_words': self._analyze_korean_words(all_text),
            'english_words': self._analyze_english_words(all_text),
            'numbers': self._analyze_numbers(all_text),
            'insurance_terms': self._analyze_insurance_terms(all_text),
            'company_terms': self._analyze_company_terms(all_text)
        }
        
        # 결과 출력
        self._print_analysis_results()
        
        return self.word_analysis
    
    def _collect_all_text(self):
        """모든 텍스트 데이터 수집"""
        all_text = ""
        
        # 1. 기본 텍스트 컬럼들
        text_columns = ['product_name', 'product_category', 'sales_channel', 
                       'premium_range', 'coverage_scope', 'waiting_period']
        
        for col in text_columns:
            if col in self.df.columns:
                text_data = self.df[col].fillna('').astype(str)
                all_text += " ".join(text_data) + " "
        
        # 2. JSON 컬럼들에서 텍스트 추출
        json_columns = ['coverage_details', 'special_coverage', 'emergency_services',
                       'partner_benefits', 'digital_services', 'discount_options',
                       'excluded_items', 'health_requirements', 'documentation_required']
        
        for col in json_columns:
            if col in self.df.columns:
                for json_str in self.df[col].fillna('[]'):
                    try:
                        if isinstance(json_str, str) and json_str.strip():
                            # JSON 파싱
                            data = json.loads(json_str)
                            extracted_text = self._extract_text_from_json(data)
                            all_text += extracted_text + " "
                    except:
                        # JSON 파싱 실패시 문자열 그대로 사용
                        all_text += str(json_str) + " "
        
        return all_text
    
    def _extract_text_from_json(self, data):
        """JSON 데이터에서 텍스트 추출"""
        text = ""
        
        if isinstance(data, dict):
            for key, value in data.items():
                text += str(key) + " " + str(value) + " "
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    text += self._extract_text_from_json(item)
                else:
                    text += str(item) + " "
        else:
            text += str(data) + " "
        
        return text
    
    def _analyze_korean_words(self, text):
        """한글 단어 분석"""
        # 한글 2글자 이상 추출
        korean_words = re.findall(r'[가-힣]{2,}', text)
        
        # 불용어 제거
        stop_words = {
            '보험', '자동차', '상품', '서비스', '고객', '가입', '지원', '제공', '포함', '경우',
            '대상', '기준', '이상', '이하', '관련', '해당', '전체', '일반', '사용', '가능',
            '필요', '확인', '신청', '계약', '약관', '조건', '내용', '정보', '방법', '절차'
        }
        
        filtered_words = [word for word in korean_words if word not in stop_words]
        word_freq = Counter(filtered_words)
        
        return {
            'total_count': len(korean_words),
            'unique_count': len(set(korean_words)),
            'top_20': dict(word_freq.most_common(20)),
            'all_frequencies': dict(word_freq)
        }
    
    def _analyze_english_words(self, text):
        """영문 단어 분석"""
        # 영문 3글자 이상 추출
        english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        
        # 불용어 제거
        stop_words = {
            'insurance', 'auto', 'car', 'service', 'customer', 'include', 'support',
            'the', 'and', 'for', 'with', 'you', 'are', 'can', 'will', 'from', 'this'
        }
        
        filtered_words = [word for word in english_words if word not in stop_words]
        word_freq = Counter(filtered_words)
        
        return {
            'total_count': len(english_words),
            'unique_count': len(set(english_words)),
            'top_15': dict(word_freq.most_common(15)),
            'all_frequencies': dict(word_freq)
        }
    
    def _analyze_numbers(self, text):
        """숫자 패턴 분석"""
        # 숫자 추출
        numbers = re.findall(r'\d+', text)
        
        # 일반적인 숫자들 (연도, 나이 등) 필터링
        filtered_numbers = []
        for num in numbers:
            num_int = int(num)
            # 보험료 관련 숫자들만 (1000 이상)
            if num_int >= 1000 or (10 <= num_int <= 100):  # 보험료 또는 나이/기간
                filtered_numbers.append(num)
        
        number_freq = Counter(filtered_numbers)
        
        return {
            'total_count': len(numbers),
            'unique_count': len(set(numbers)),
            'top_15': dict(number_freq.most_common(15)),
            'common_ranges': self._categorize_numbers(filtered_numbers)
        }
    
    def _categorize_numbers(self, numbers):
        """숫자를 카테고리별로 분류"""
        categories = {
            '나이_관련': [],      # 18-70
            '보험료_관련': [],    # 10000 이상
            '연도_관련': [],      # 2000 이상
            '기타_숫자': []
        }
        
        for num_str in numbers:
            try:
                num = int(num_str)
                if 18 <= num <= 70:
                    categories['나이_관련'].append(num_str)
                elif num >= 10000:
                    categories['보험료_관련'].append(num_str)
                elif 2000 <= num <= 2030:
                    categories['연도_관련'].append(num_str)
                else:
                    categories['기타_숫자'].append(num_str)
            except:
                categories['기타_숫자'].append(num_str)
        
        # 각 카테고리별 빈도
        result = {}
        for category, nums in categories.items():
            if nums:
                freq = Counter(nums)
                result[category] = dict(freq.most_common(5))
        
        return result
    
    def _analyze_insurance_terms(self, text):
        """보험 전문용어 분석"""
        insurance_terms = [
            '대인배상', '대물배상', '자차보험', '자기신체사고', '무보험차상해',
            '출동서비스', '견인서비스', '렌터카', '할인', '특약', '면책',
            '다이렉트', '종합보험', '책임보험', '운전자보험', '상해보험',
            '무사고할인', '다자녀할인', '블랙박스할인', '하이브리드할인',
            '긴급출동', '현장출동', '대리운전', '정비할인', '주유할인'
        ]
        
        term_freq = {}
        for term in insurance_terms:
            count = text.count(term)
            if count > 0:
                term_freq[term] = count
        
        return dict(sorted(term_freq.items(), key=lambda x: x[1], reverse=True))
    
    def _analyze_company_terms(self, text):
        """보험사 관련 용어 분석"""
        companies = [
            '삼성화재', '현대해상', 'KB손해보험', '메리츠화재', 'DB손해보험',
            '롯데손해보험', '한화손해보험', 'MG손해보험', '흥국화재', 'AXA손해보험',
            '하나손해보험', '캐롯손해보험'
        ]
        
        company_freq = {}
        for company in companies:
            # 정확한 회사명과 단축명 모두 체크
            short_name = company.replace('화재해상보험', '').replace('손해보험', '')
            count = text.count(company) + text.count(short_name)
            if count > 0:
                company_freq[company] = count
        
        return dict(sorted(company_freq.items(), key=lambda x: x[1], reverse=True))
    
    def _print_analysis_results(self):
        """분석 결과 출력"""
        
        print(f"\n{'='*60}")
        print(f"📊 단어 빈도 분석 결과")
        print(f"{'='*60}")
        
        # 1. 한글 단어 TOP 20
        print(f"\n🇰🇷 한글 단어 TOP 20:")
        korean_top = self.word_analysis['korean_words']['top_20']
        for i, (word, count) in enumerate(korean_top.items(), 1):
            print(f"  {i:2d}. {word}: {count}회")
        
        # 2. 영문 단어 TOP 15
        print(f"\n🇺🇸 영문 단어 TOP 15:")
        english_top = self.word_analysis['english_words']['top_15']
        for i, (word, count) in enumerate(english_top.items(), 1):
            print(f"  {i:2d}. {word}: {count}회")
        
        # 3. 보험 전문용어
        print(f"\n🏥 보험 전문용어 빈도:")
        insurance_terms = self.word_analysis['insurance_terms']
        for i, (term, count) in enumerate(insurance_terms.items(), 1):
            if i <= 10:  # 상위 10개만
                print(f"  {i:2d}. {term}: {count}회")
        
        # 4. 숫자 분석
        print(f"\n🔢 주요 숫자 TOP 10:")
        numbers_top = self.word_analysis['numbers']['top_15']
        for i, (num, count) in enumerate(list(numbers_top.items())[:10], 1):
            print(f"  {i:2d}. {num}: {count}회")
        
        # 5. 보험사별 언급 빈도
        print(f"\n🏢 보험사별 언급 빈도:")
        company_terms = self.word_analysis['company_terms']
        for i, (company, count) in enumerate(company_terms.items(), 1):
            if i <= 12:  # 모든 보험사
                print(f"  {i:2d}. {company}: {count}회")
        
        # 6. 통계 요약
        print(f"\n📈 통계 요약:")
        print(f"  총 한글 단어: {self.word_analysis['korean_words']['total_count']:,}개")
        print(f"  고유 한글 단어: {self.word_analysis['korean_words']['unique_count']:,}개")
        print(f"  총 영문 단어: {self.word_analysis['english_words']['total_count']:,}개")
        print(f"  고유 영문 단어: {self.word_analysis['english_words']['unique_count']:,}개")
        print(f"  발견된 보험 전문용어: {len(insurance_terms)}개")
    
    def save_analysis_to_csv(self, output_prefix='word_analysis'):
        """분석 결과를 CSV로 저장"""
        
        if not self.word_analysis:
            print("❌ 분석을 먼저 실행해주세요.")
            return
        
        try:
            # 1. 한글 단어 빈도
            korean_df = pd.DataFrame(list(self.word_analysis['korean_words']['all_frequencies'].items()),
                                   columns=['단어', '빈도'])
            korean_df = korean_df.sort_values('빈도', ascending=False)
            korean_df.to_csv(f'{output_prefix}_korean_words.csv', index=False, encoding='utf-8-sig')
            
            # 2. 영문 단어 빈도
            english_df = pd.DataFrame(list(self.word_analysis['english_words']['all_frequencies'].items()),
                                    columns=['Word', 'Frequency'])
            english_df = english_df.sort_values('Frequency', ascending=False)
            english_df.to_csv(f'{output_prefix}_english_words.csv', index=False, encoding='utf-8-sig')
            
            # 3. 보험 전문용어
            if self.word_analysis['insurance_terms']:
                terms_df = pd.DataFrame(list(self.word_analysis['insurance_terms'].items()),
                                      columns=['보험용어', '빈도'])
                terms_df.to_csv(f'{output_prefix}_insurance_terms.csv', index=False, encoding='utf-8-sig')
            
            # 4. 종합 요약
            summary_data = {
                '분석_항목': ['총 한글단어', '고유 한글단어', '총 영문단어', '고유 영문단어', '보험전문용어'],
                '개수': [
                    self.word_analysis['korean_words']['total_count'],
                    self.word_analysis['korean_words']['unique_count'],
                    self.word_analysis['english_words']['total_count'],
                    self.word_analysis['english_words']['unique_count'],
                    len(self.word_analysis['insurance_terms'])
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(f'{output_prefix}_summary.csv', index=False, encoding='utf-8-sig')
            
            print(f"\n💾 분석 결과 저장 완료:")
            print(f"  - {output_prefix}_korean_words.csv")
            print(f"  - {output_prefix}_english_words.csv")
            print(f"  - {output_prefix}_insurance_terms.csv")
            print(f"  - {output_prefix}_summary.csv")
            
        except Exception as e:
            print(f"❌ 저장 실패: {str(e)}")

# 사용 예시
def main():
    """메인 실행 함수"""
    
    print("=== CSV 파일 단어 빈도 분석기 ===")
    
    # CSV 파일 경로 (수정 필요)
    csv_file_path = "detailed_insurance_products.csv"  # ← 여기를 실제 CSV 파일 경로로 변경
    
    # 분석기 초기화
    analyzer = WordFrequencyAnalyzer(csv_file_path)
    
    # CSV 로드
    if not analyzer.load_csv():
        print("💡 CSV 파일 경로를 확인해주세요.")
        return
    
    # 단어 빈도 분석 실행
    word_analysis = analyzer.analyze_word_frequency()
    
    # 결과를 CSV로 저장
    analyzer.save_analysis_to_csv('insurance_word_analysis')
    
    print(f"\n🎉 분석 완료!")
    print(f"결과 파일들이 생성되었습니다.")

if __name__ == "__main__":
    main()

# 필요한 라이브러리
print("\n📦 필요한 라이브러리:")
print("pip install pandas matplotlib seaborn")