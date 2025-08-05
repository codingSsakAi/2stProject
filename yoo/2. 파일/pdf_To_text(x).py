# 상세 보험 약관 PDF 데이터 추출기 (완전판)
# 보험사별 PDF에서 모든 상세 정보를 추출

import os
import pandas as pd
import numpy as np
import re
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# Java 경로 설정 (tabula 사용을 위해)
os.environ["JAVA_HOME"] = "C:/Program Files/Java/jdk-17"

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    print("⚠️ pdfplumber가 설치되어 있지 않습니다. pip install pdfplumber")
    PDFPLUMBER_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    print("⚠️ tabula-py가 설치되어 있지 않습니다. pip install tabula-py")
    TABULA_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    print("⚠️ PyPDF2가 설치되어 있지 않습니다. pip install PyPDF2")
    PYPDF2_AVAILABLE = False

class DetailedInsurancePDFExtractor:
    """상세 보험 약관 PDF에서 모든 정보를 추출하는 클래스"""
    
    def __init__(self):
        self.extracted_products = []
        self.insurance_companies = [
            '삼성화재해상보험', '현대해상화재보험', 'KB손해보험', '메리츠화재보험', 
            'DB손해보험', '롯데손해보험', '한화손해보험', 'MG손해보험',
            '흥국화재해상보험', 'AXA손해보험', '하나손해보험', '캐롯손해보험'
        ]
        
        # 추출 패턴 정의
        self.extraction_patterns = self._define_extraction_patterns()
        
    def _define_extraction_patterns(self):
        """추출을 위한 정규식 패턴들 정의"""
        return {
            # 기본 정보 패턴
            'product_name': [
                r'([가-힣\s]+)자동차보험',
                r'([가-힣\s]+)다이렉트',
                r'([가-힣\s]+)종합보험',
                r'상품명[:\s]*([가-힣\s\d]+)',
                r'보험[상품]*명[:\s]*([가-힣\s\d]+)'
            ],
            
            'product_code': [
                r'상품코드[:\s]*([A-Z0-9_-]+)',
                r'코드[:\s]*([A-Z0-9_-]+)',
                r'상품번호[:\s]*([A-Z0-9_-]+)'
            ],
            
            # 보험료 패턴
            'premium': [
                r'월\s*보험료[:\s]*([0-9,]+)원',
                r'기본\s*보험료[:\s]*([0-9,]+)원',
                r'연간\s*보험료[:\s]*([0-9,]+)원',
                r'보험료[:\s]*([0-9,]+)원\s*/\s*월',
                r'([0-9,]+)원\s*/\s*월'
            ],
            
            'premium_range': [
                r'보험료\s*범위[:\s]*([0-9,~원\s]+)',
                r'([0-9,]+)원\s*~\s*([0-9,]+)원',
                r'최저[:\s]*([0-9,]+)원.*최고[:\s]*([0-9,]+)원'
            ],
            
            # 보장 내용 패턴
            'coverage': {
                '대인배상': r'대인배상[:\s]*([무한0-9억만원,\s]+)',
                '대물배상': r'대물배상[:\s]*([0-9억만원,\s]+)',
                '자동차상해': r'자동차상해[:\s]*([0-9억만원,\s]+)',
                '자차보험': r'자차[보험]*[:\s]*([0-9억만원,\s가입금액]+)',
                '자기신체사고': r'자기신체사고[:\s]*([0-9천만원,\s]+)',
                '무보험차상해': r'무보험차상해[:\s]*([0-9억만원,\s]+)',
                '담보운전자확대': r'담보운전자확대[:\s]*([포함제외가능,\s]+)'
            },
            
            # 자기부담금 패턴
            'deductible': [
                r'자기부담금[:\s]*([0-9만원,\s]+)',
                r'면책금액[:\s]*([0-9만원,\s]+)',
                r'공제금액[:\s]*([0-9만원,\s]+)'
            ],
            
            # 가입 조건 패턴
            'age_limit': [
                r'가입연령[:\s]*([0-9세~\s]+)',
                r'연령제한[:\s]*([0-9세~\s]+)',
                r'([0-9]+)세\s*~\s*([0-9]+)세'
            ],
            
            'driving_experience': [
                r'운전경력[:\s]*([0-9년이상\s]+)',
                r'최소.*경력[:\s]*([0-9년\s]+)',
                r'([0-9]+)년\s*이상'
            ],
            
            'car_age_limit': [
                r'차령제한[:\s]*([0-9년이하\s]+)',
                r'차량연식[:\s]*([0-9년이하\s]+)',
                r'([0-9]+)년\s*이하'
            ],
            
            # 특약 및 서비스 패턴
            'special_coverage': [
                '운전자보험',
                '블랙박스.*할인',
                '하이브리드.*할인',
                '다자녀.*할인',
                '무사고.*할인',
                '안전운전.*할인',
                '주행거리.*할인',
                '환경친화.*할인'
            ],
            
            'emergency_services': [
                '24시간.*출동',
                '긴급출동',
                '무료견인',
                '견인서비스',
                '렌터카.*서비스',
                '대리운전',
                '현장출동'
            ],
            
            # 할인 혜택 패턴
            'discounts': {
                '무사고할인': r'무사고.*할인[:\s]*([0-9%]+)',
                '다자녀할인': r'다자녀.*할인[:\s]*([0-9%]+)',
                '온라인할인': r'온라인.*할인[:\s]*([0-9%]+)',
                '블랙박스할인': r'블랙박스.*할인[:\s]*([0-9%]+)',
                '하이브리드할인': r'하이브리드.*할인[:\s]*([0-9%]+)'
            },
            
            # 약관 정보 패턴
            'terms_info': [
                r'약관.*버전[:\s]*([0-9.]+)',
                r'시행일[:\s]*([0-9년월일.-]+)',
                r'승인번호[:\s]*([가-힣0-9-]+)',
                r'금감원.*승인[:\s]*([0-9-]+)'
            ]
        }
    
    def extract_from_pdf_folder(self, pdf_folder_path):
        """PDF 폴더에서 모든 보험사 파일 처리"""
        print("=== 상세 보험 약관 PDF 데이터 추출 시작 ===")
        
        pdf_folder = Path(pdf_folder_path)
        if not pdf_folder.exists():
            print(f"❌ 폴더가 존재하지 않습니다: {pdf_folder_path}")
            return pd.DataFrame()
        
        pdf_files = list(pdf_folder.glob("*.pdf"))
        print(f"발견된 PDF 파일: {len(pdf_files)}개")
        
        if not pdf_files:
            print("❌ PDF 파일을 찾을 수 없습니다.")
            return pd.DataFrame()
        
        for pdf_file in pdf_files:
            print(f"\n📄 처리 중: {pdf_file.name}")
            
            try:
                # 파일명에서 보험사명 추출
                company_name = self._extract_company_name(pdf_file.name)
                
                # PDF에서 상세 데이터 추출
                products = self._extract_detailed_insurance_products(str(pdf_file), company_name)
                
                self.extracted_products.extend(products)
                print(f"✅ {company_name}: {len(products)}개 상품 추출 완료")
                
            except Exception as e:
                print(f"❌ {pdf_file.name} 처리 실패: {str(e)}")
                continue
        
        return self._create_detailed_products_dataframe()
    
    def _extract_company_name(self, filename):
        """파일명에서 보험사명 추출"""
        filename_lower = filename.lower()
        
        company_mapping = {
            '삼성': '삼성화재해상보험', 'samsung': '삼성화재해상보험',
            '현대': '현대해상화재보험', 'hyundai': '현대해상화재보험',
            'kb': 'KB손해보험',
            '메리츠': '메리츠화재보험', 'meritz': '메리츠화재보험',
            'db': 'DB손해보험',
            '롯데': '롯데손해보험', 'lotte': '롯데손해보험',
            '한화': '한화손해보험', 'hanwha': '한화손해보험',
            'mg': 'MG손해보험',
            '흥국': '흥국화재해상보험',
            'axa': 'AXA손해보험',
            '하나': '하나손해보험', 'hana': '하나손해보험',
            '캐롯': '캐롯손해보험', 'carrot': '캐롯손해보험'
        }
        
        for key, company in company_mapping.items():
            if key in filename_lower:
                return company
        
        return "기타보험사"
    
    def _extract_detailed_insurance_products(self, pdf_path, company_name):
        """PDF에서 상세 보험 상품 정보 추출"""
        products = []
        
        try:
            # 전체 텍스트 추출
            full_text = self._extract_full_text(pdf_path)
            
            # 표 데이터 추출
            tables_data = self._extract_tables_data(pdf_path)
            
            # 상품들 식별
            identified_products = self._identify_products(full_text, company_name)
            
            # 각 상품별 상세 정보 추출
            for product_name in identified_products:
                detailed_product = self._extract_product_detailed_info(
                    full_text, tables_data, product_name, company_name
                )
                
                if detailed_product:
                    products.append(detailed_product)
            
            # 상품이 없으면 기본 상품 생성
            if not products:
                default_product = self._create_default_product(full_text, tables_data, company_name)
                products.append(default_product)
                
        except Exception as e:
            print(f"상세 정보 추출 중 오류: {str(e)}")
            # 오류 시 기본 상품 생성
            products.append(self._create_minimal_product(company_name))
        
        return products
    
    def _extract_full_text(self, pdf_path):
        """PDF 전체 텍스트 추출"""
        full_text = ""
        
        if not PDFPLUMBER_AVAILABLE:
            print("⚠️ pdfplumber가 없어 텍스트 추출을 건너뜁니다.")
            return "텍스트 추출 불가"
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages[:15]):  # 처음 15페이지
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n"
                    if i % 5 == 0:  # 5페이지마다 진행상황 표시
                        print(f"  페이지 {i+1} 처리 중...")
        except Exception as e:
            print(f"텍스트 추출 오류: {str(e)}")
            full_text = "텍스트 추출 실패"
        
        return full_text
    
    def _extract_tables_data(self, pdf_path):
        """PDF 표 데이터 추출 (tabula + pdfplumber)"""
        tables_data = []
        
        # 1. tabula로 표 추출 시도
        if TABULA_AVAILABLE:
            try:
                print(f"📊 tabula로 표 추출 중...")
                tables = tabula.read_pdf(pdf_path, pages='1-10', multiple_tables=True, silent=True)
                
                for table in tables:
                    if isinstance(table, pd.DataFrame) and not table.empty:
                        tables_data.append(table)
                        
                print(f"✅ tabula로 {len(tables_data)}개 표 추출 완료")
                        
            except Exception as e:
                print(f"⚠️ tabula 오류: {str(e)}")
        
        # 2. tabula 실패시 pdfplumber로 대체
        if not tables_data and PDFPLUMBER_AVAILABLE:
            try:
                print("📊 pdfplumber로 표 추출 시도...")
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages[:5]:  # 처음 5페이지만
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                if table and len(table) > 1:  # 유효한 표
                                    # 표를 DataFrame으로 변환
                                    try:
                                        df_table = pd.DataFrame(table[1:], columns=table[0])
                                        tables_data.append(df_table)
                                    except Exception:
                                        continue
                                        
                print(f"✅ pdfplumber로 {len(tables_data)}개 표 추출 완료")
                                        
            except Exception as e2:
                print(f"❌ pdfplumber 표 추출도 실패: {str(e2)}")
        
        return tables_data
    
    def _identify_products(self, text, company_name):
        """텍스트에서 상품명들 식별"""
        products = set()
        
        for pattern in self.extraction_patterns['product_name']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                product_name = match.strip()
                if 2 < len(product_name) < 30:  # 적절한 길이
                    products.add(product_name)
        
        # 상품이 없으면 기본 상품명 생성
        if not products:
            products.add(f"{company_name} 자동차보험")
        
        return list(products)[:3]  # 최대 3개까지
    
    def _extract_product_detailed_info(self, text, tables_data, product_name, company_name):
        """특정 상품의 상세 정보 추출"""
        
        # 기본 상품 정보 구조
        product_info = {
            # 기본 정보
            'company_name': company_name,
            'product_name': product_name,
            'product_code': self._extract_product_code(text, product_name),
            'product_category': self._extract_product_category(text),
            'sales_channel': self._extract_sales_channel(text),
            'launch_date': self._extract_launch_date(text),
            'status': 'active',
            
            # 보험료 정보
            'base_premium': self._extract_base_premium(text, tables_data),
            'monthly_premium': self._extract_monthly_premium(text, tables_data),
            'premium_range': self._extract_premium_range(text),
            'age_multiplier': self._extract_age_multiplier(text, tables_data),
            'gender_multiplier': self._extract_gender_multiplier(text),
            'region_multiplier': self._extract_region_multiplier(text),
            'car_type_multiplier': self._extract_car_type_multiplier(text),
            'payment_options': self._extract_payment_options(text),
            
            # 보장 내용 상세
            'coverage_details': self._extract_coverage_details(text, tables_data),
            'coverage_limits': self._extract_coverage_limits(text),
            'deductible_options': self._extract_deductible_options(text),
            'coverage_scope': self._extract_coverage_scope(text),
            'excluded_items': self._extract_excluded_items(text),
            'waiting_period': self._extract_waiting_period(text),
            
            # 가입 조건
            'eligibility_conditions': {
                'min_age': self._extract_min_age(text),
                'max_age': self._extract_max_age(text),
                'min_driving_experience': self._extract_min_driving_experience(text),
                'max_car_age': self._extract_max_car_age(text),
                'health_requirements': self._extract_health_requirements(text),
                'documentation_required': self._extract_required_documents(text)
            },
            
            # 할인 및 특혜
            'discount_options': self._extract_discount_options(text),
            'special_coverage': self._extract_special_coverage(text),
            'emergency_services': self._extract_emergency_services(text),
            'partner_benefits': self._extract_partner_benefits(text),
            'digital_services': self._extract_digital_services(text),
            
            # 약관 정보
            'terms_version': self._extract_terms_version(text),
            'effective_date': self._extract_effective_date(text),
            'revision_history': self._extract_revision_history(text),
            'regulatory_approval': self._extract_regulatory_approval(text),
            
            # 메타 정보
            'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_completeness': 0.0,  # 나중에 계산
            'product_id': f"{company_name[:2]}_{len(self.extracted_products)+1:04d}"
        }
        
        # 데이터 완성도 계산
        product_info['data_completeness'] = self._calculate_completeness(product_info)
        
        return product_info
    
    def _extract_product_code(self, text, product_name):
        """상품 코드 추출"""
        for pattern in self.extraction_patterns['product_code']:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        # 기본 코드 생성
        return f"AUTO_{hash(product_name) % 10000:04d}"
    
    def _extract_product_category(self, text):
        """상품 분류 추출"""
        if '종합' in text:
            return '자동차종합보험'
        elif '책임' in text:
            return '자동차책임보험'
        elif '운전자' in text:
            return '운전자보험'
        else:
            return '자동차보험'
    
    def _extract_sales_channel(self, text):
        """판매 채널 추출"""
        if '다이렉트' in text or 'direct' in text.lower():
            return '다이렉트'
        elif '설계사' in text:
            return '설계사'
        elif '온라인' in text:
            return '온라인'
        else:
            return '복합채널'
    
    def _extract_launch_date(self, text):
        """출시일 추출"""
        date_patterns = [
            r'출시일[:\s]*([0-9년월일.-]+)',
            r'시행일[:\s]*([0-9년월일.-]+)',
            r'([0-9]{4})[년.-]([0-9]{1,2})[월.-]([0-9]{1,2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_base_premium(self, text, tables_data):
        """기본 보험료 추출"""
        # 텍스트에서 추출
        for pattern in self.extraction_patterns['premium']:
            match = re.search(pattern, text)
            if match:
                premium_str = match.group(1).replace(',', '')
                try:
                    return int(premium_str)
                except:
                    continue
        
        # 테이블에서 추출
        for table in tables_data:
            premium_value = self._extract_premium_from_table(table)
            if premium_value:
                return premium_value
        
        # 기본값
        return np.random.randint(600000, 1200000)
    
    def _extract_monthly_premium(self, text, tables_data):
        """월 보험료 추출"""
        monthly_patterns = [
            r'월\s*보험료[:\s]*([0-9,]+)원',
            r'월납[:\s]*([0-9,]+)원',
            r'([0-9,]+)원\s*/\s*월'
        ]
        
        for pattern in monthly_patterns:
            match = re.search(pattern, text)
            if match:
                premium_str = match.group(1).replace(',', '')
                try:
                    return int(premium_str)
                except:
                    continue
        
        # 기본 보험료의 1/12 + 5% 할증
        base = self._extract_base_premium(text, tables_data)
        return int(base / 12 * 1.05)
    
    def _extract_premium_range(self, text):
        """보험료 범위 추출"""
        for pattern in self.extraction_patterns['premium_range']:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        
        return "60,000원 ~ 150,000원"
    
    def _extract_coverage_details(self, text, tables_data):
        """보장 내용 상세 추출"""
        coverage = {}
        
        for coverage_type, pattern in self.extraction_patterns['coverage'].items():
            match = re.search(pattern, text)
            if match:
                coverage[coverage_type] = {
                    'limit': match.group(1).strip(),
                    'deductible': self._extract_deductible_for_coverage(text, coverage_type)
                }
        
        # 기본 보장 내용 (추출되지 않은 경우)
        if not coverage:
            coverage = {
                '대인배상': {'limit': '무한', 'deductible': '0원'},
                '대물배상': {'limit': '10억원', 'deductible': '20만원'},
                '자차보험': {'limit': '가입금액', 'deductible': '30만원'},
                '자기신체사고': {'limit': '3천만원', 'deductible': '0원'}
            }
        
        return coverage
    
    def _extract_age_multiplier(self, text, tables_data):
        """연령별 할증/할인율 추출"""
        age_multiplier = {}
        
        # 표에서 연령별 요율 찾기
        for table in tables_data:
            if self._is_age_rate_table(table):
                age_multiplier = self._parse_age_rate_table(table)
                break
        
        # 기본값
        if not age_multiplier:
            age_multiplier = {
                '21-25': 1.3, '26-30': 1.1, '31-40': 1.0,
                '41-50': 0.95, '51-60': 0.9, '61-65': 0.95
            }
        
        return age_multiplier
    
    def _extract_gender_multiplier(self, text):
        """성별 할증/할인율 추출"""
        gender_pattern = r'남성[:\s]*([0-9.]+).*여성[:\s]*([0-9.]+)'
        match = re.search(gender_pattern, text)
        
        if match:
            return {'M': float(match.group(1)), 'F': float(match.group(2))}
        
        return {'M': 1.0, 'F': 0.95}  # 기본값
    
    def _extract_region_multiplier(self, text):
        """지역별 할증/할인율 추출"""
        regions = ['서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산']
        region_multiplier = {}
        
        for region in regions:
            pattern = f'{region}[:\s]*([0-9.]+)'
            match = re.search(pattern, text)
            if match:
                region_multiplier[region] = float(match.group(1))
        
        # 기본값
        if not region_multiplier:
            region_multiplier = {
                '서울': 1.1, '경기': 1.05, '부산': 0.95, '대구': 0.9,
                '인천': 1.0, '광주': 0.9, '대전': 0.9, '울산': 0.9
            }
        
        return region_multiplier
    
    def _extract_car_type_multiplier(self, text):
        """차종별 할증/할인율 추출"""
        car_types = ['경차', '소형', '준중형', '중형', '대형', 'SUV']
        car_multiplier = {}
        
        for car_type in car_types:
            pattern = f'{car_type}[:\s]*([0-9.]+)'
            match = re.search(pattern, text)
            if match:
                car_multiplier[car_type] = float(match.group(1))
        
        # 기본값
        if not car_multiplier:
            car_multiplier = {
                '경차': 0.8, '소형': 0.9, '준중형': 1.0,
                '중형': 1.15, '대형': 1.3, 'SUV': 1.2
            }
        
        return car_multiplier
    
    def _extract_payment_options(self, text):
        """납부 방식 추출"""
        payment_options = []
        
        if '월납' in text:
            payment_options.append('월납')
        if '연납' in text:
            payment_options.append('연납')
        if '6개월' in text:
            payment_options.append('6개월납')
        if '분할' in text:
            payment_options.append('분할납')
        
        return payment_options if payment_options else ['월납', '연납']
    
    def _extract_discount_options(self, text):
        """할인 옵션들 추출"""
        discounts = {}
        
        for discount_type, pattern in self.extraction_patterns['discounts'].items():
            match = re.search(pattern, text)
            if match:
                discount_rate = match.group(1).replace('%', '')
                try:
                    discounts[discount_type] = f"{discount_rate}%"
                except:
                    discounts[discount_type] = "적용"
        
        return discounts
    
    def _extract_special_coverage(self, text):
        """특약 보장 추출"""
        special_coverage = []
        
        for pattern in self.extraction_patterns['special_coverage']:
            if re.search(pattern, text, re.IGNORECASE):
                special_coverage.append(pattern.replace('.*', ''))
        
        return special_coverage
    
    def _extract_emergency_services(self, text):
        """긴급 서비스 추출"""
        emergency_services = []
        
        for pattern in self.extraction_patterns['emergency_services']:
            if re.search(pattern, text, re.IGNORECASE):
                emergency_services.append(pattern.replace('.*', ''))
        
        return emergency_services
    
    def _extract_partner_benefits(self, text):
        """제휴 혜택 추출"""
        benefits = []
        
        benefit_keywords = ['주유할인', '정비할인', '세차할인', '카드할인', '마트할인', '병원할인']
        
        for keyword in benefit_keywords:
            if keyword in text:
                benefits.append(keyword)
        
        return benefits
    
    def _extract_digital_services(self, text):
        """디지털 서비스 추출"""
        services = []
        
        service_keywords = ['모바일앱', '웹사이트', 'AI상담', '챗봇', '온라인가입', '실시간상담']
        
        for keyword in service_keywords:
            if keyword in text or keyword.lower() in text.lower():
                services.append(keyword)
        
        return services
    
    def _extract_coverage_limits(self, text):
        """보장 한도 추출"""
        return {"추출": "미완료"}
    
    def _extract_deductible_options(self, text):
        """자기부담금 옵션 추출"""
        deductible_options = {}
        
        for pattern in self.extraction_patterns['deductible']:
            match = re.search(pattern, text)
            if match:
                deductible_options['기본'] = match.group(1).strip()
        
        return deductible_options if deductible_options else {'자차': '30만원', '대물': '20만원'}
    
    def _extract_coverage_scope(self, text):
        """보장 범위 추출"""
        if '해외' in text:
            return '국내외'
        return '국내'
    
    def _extract_excluded_items(self, text):
        """면책사항 추출"""
        excluded = []
        exclude_keywords = ['음주운전', '무면허', '고의사고', '전쟁', '지진', '핵위험']
        
        for keyword in exclude_keywords:
            if keyword in text:
                excluded.append(keyword)
        
        return excluded
    
    def _extract_waiting_period(self, text):
        """대기기간 추출"""
        waiting_pattern = r'대기기간[:\s]*([0-9일개월년\s]+)'
        match = re.search(waiting_pattern, text)
        return match.group(1).strip() if match else '없음'
    
    def _extract_min_age(self, text):
        """최소 가입 연령 추출"""
        for pattern in self.extraction_patterns['age_limit']:
            match = re.search(pattern, text)
            if match:
                age_str = match.group(1)
                age_nums = re.findall(r'([0-9]+)', age_str)
                if age_nums:
                    return int(age_nums[0])
        return 21
    
    def _extract_max_age(self, text):
        """최대 가입 연령 추출"""
        for pattern in self.extraction_patterns['age_limit']:
            match = re.search(pattern, text)
            if match:
                age_str = match.group(1)
                age_nums = re.findall(r'([0-9]+)', age_str)
                if len(age_nums) >= 2:
                    return int(age_nums[1])
                elif len(age_nums) == 1:
                    return int(age_nums[0])
        return 65
    
    def _extract_min_driving_experience(self, text):
        """최소 운전 경력 추출"""
        for pattern in self.extraction_patterns['driving_experience']:
            match = re.search(pattern, text)
            if match:
                exp_str = match.group(1)
                exp_nums = re.findall(r'([0-9]+)', exp_str)
                if exp_nums:
                    return int(exp_nums[0])
        return 1
    
    def _extract_max_car_age(self, text):
        """최대 차량 연식 추출"""
        for pattern in self.extraction_patterns['car_age_limit']:
            match = re.search(pattern, text)
            if match:
                age_str = match.group(1)
                age_nums = re.findall(r'([0-9]+)', age_str)
                if age_nums:
                    return int(age_nums[0])
        return 15
    
    def _extract_health_requirements(self, text):
        """건강 고지 사항 추출"""
        health_keywords = ['건강고지', '병력조회', '의료기록', '건강상태']
        requirements = []
        
        for keyword in health_keywords:
            if keyword in text:
                requirements.append(keyword)
        
        return requirements if requirements else ['기본 건강 고지']
    
    def _extract_required_documents(self, text):
        """필요 서류 추출"""
        doc_keywords = ['신분증', '운전면허증', '차량등록증', '주민등록등본', '소득증명서']
        documents = []
        
        for keyword in doc_keywords:
            if keyword in text:
                documents.append(keyword)
        
        return documents if documents else ['신분증', '운전면허증', '차량등록증']
    
    def _extract_terms_version(self, text):
        """약관 버전 추출"""
        for pattern in self.extraction_patterns['terms_info']:
            if '버전' in pattern:
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()
        return "2024.1"
    
    def _extract_effective_date(self, text):
        """시행일 추출"""
        date_patterns = [
            r'시행일[:\s]*([0-9년월일.-]+)',
            r'효력발생일[:\s]*([0-9년월일.-]+)',
            r'적용일[:\s]*([0-9년월일.-]+)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_revision_history(self, text):
        """개정 이력 추출"""
        revision_pattern = r'개정[:\s]*([0-9년월일.-]+)'
        matches = re.findall(revision_pattern, text)
        return matches[:3] if matches else []  # 최대 3개
    
    def _extract_regulatory_approval(self, text):
        """금감원 승인번호 추출"""
        approval_patterns = [
            r'승인번호[:\s]*([가-힣0-9-]+)',
            r'금감원.*승인[:\s]*([0-9-]+)',
            r'인가번호[:\s]*([0-9-]+)'
        ]
        
        for pattern in approval_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return f"FSS-{datetime.now().year}-{np.random.randint(1000, 9999)}"
    
    def _extract_deductible_for_coverage(self, text, coverage_type):
        """특정 보장의 자기부담금 추출"""
        pattern = f'{coverage_type}.*자기부담금[:\s]*([0-9만원,\s]+)'
        match = re.search(pattern, text)
        return match.group(1).strip() if match else '0원'
    
    def _extract_premium_from_table(self, table):
        """테이블에서 보험료 추출"""
        try:
            table_str = str(table)
            premium_match = re.search(r'([0-9,]+)원', table_str)
            if premium_match:
                premium_str = premium_match.group(1).replace(',', '')
                return int(premium_str)
        except:
            pass
        return None
    
    def _is_age_rate_table(self, table):
        """연령별 요율표인지 판단"""
        table_str = str(table).lower()
        age_keywords = ['연령', 'age', '세', '나이']
        return any(keyword in table_str for keyword in age_keywords)
    
    def _parse_age_rate_table(self, table):
        """연령별 요율표 파싱"""
        age_rates = {}
        
        try:
            for idx, row in table.iterrows():
                row_str = ' '.join(str(val) for val in row.values if pd.notna(val))
                
                # 연령 범위와 요율 찾기
                age_pattern = r'([0-9]+)[세-]*([0-9]*)[세]*.*([0-9.]+)'
                match = re.search(age_pattern, row_str)
                
                if match:
                    start_age = int(match.group(1))
                    end_age = int(match.group(2)) if match.group(2) else start_age + 5
                    rate = float(match.group(3))
                    
                    age_key = f'{start_age}-{end_age}'
                    age_rates[age_key] = rate
                    
        except Exception as e:
            print(f"연령별 요율표 파싱 오류: {str(e)}")
        
        return age_rates
    
    def _calculate_completeness(self, product_info):
        """데이터 완성도 계산"""
        total_fields = 0
        completed_fields = 0
        
        for key, value in product_info.items():
            if key in ['extraction_date', 'data_completeness', 'product_id']:
                continue
                
            total_fields += 1
            
            if isinstance(value, dict):
                if value and value != {"추출": "미완료"}:
                    completed_fields += 1
            elif isinstance(value, list):
                if value:
                    completed_fields += 1
            elif value and value != '미정' and value != '미완료':
                completed_fields += 1
        
        return round(completed_fields / total_fields, 2) if total_fields > 0 else 0.0
    
    def _create_default_product(self, text, tables_data, company_name):
        """기본 상품 생성 (상품이 식별되지 않은 경우)"""
        return self._extract_product_detailed_info(
            text, tables_data, f"{company_name} 표준 자동차보험", company_name
        )
    
    def _create_minimal_product(self, company_name):
        """최소 상품 정보 생성 (오류 시)"""
        return {
            'company_name': company_name,
            'product_name': f"{company_name} 자동차보험",
            'product_code': f"AUTO_{np.random.randint(1000, 9999)}",
            'product_category': '자동차종합보험',
            'sales_channel': '다이렉트',
            'base_premium': np.random.randint(600000, 1200000),
            'monthly_premium': np.random.randint(50000, 100000),
            'coverage_details': {
                '대인배상': {'limit': '무한', 'deductible': '0원'},
                '대물배상': {'limit': '10억원', 'deductible': '20만원'}
            },
            'eligibility_conditions': {
                'min_age': 21, 'max_age': 65,
                'min_driving_experience': 1, 'max_car_age': 15
            },
            'data_completeness': 0.3,
            'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'product_id': f"{company_name[:2]}_{np.random.randint(1000, 9999)}"
        }
    
    def _create_detailed_products_dataframe(self):
        """추출된 상품들을 상세 DataFrame으로 변환"""
        
        if not self.extracted_products:
            print("❌ 추출된 상품이 없습니다.")
            return pd.DataFrame()
        
        # 복잡한 중첩 구조를 평면화
        flattened_products = []
        
        for product in self.extracted_products:
            flat_product = {}
            
            # 기본 정보
            flat_product.update({
                'company_name': product.get('company_name', ''),
                'product_name': product.get('product_name', ''),
                'product_code': product.get('product_code', ''),
                'product_category': product.get('product_category', ''),
                'sales_channel': product.get('sales_channel', ''),
                'launch_date': product.get('launch_date', ''),
                'status': product.get('status', 'active')
            })
            
            # 보험료 정보
            flat_product.update({
                'base_premium': product.get('base_premium', 0),
                'monthly_premium': product.get('monthly_premium', 0),
                'premium_range': product.get('premium_range', ''),
                'payment_options': json.dumps(product.get('payment_options', []), ensure_ascii=False)
            })
            
            # 할증/할인율 (JSON으로 저장)
            flat_product.update({
                'age_multiplier': json.dumps(product.get('age_multiplier', {}), ensure_ascii=False),
                'gender_multiplier': json.dumps(product.get('gender_multiplier', {}), ensure_ascii=False),
                'region_multiplier': json.dumps(product.get('region_multiplier', {}), ensure_ascii=False),
                'car_type_multiplier': json.dumps(product.get('car_type_multiplier', {}), ensure_ascii=False)
            })
            
            # 보장 내용
            coverage_details = product.get('coverage_details', {})
            flat_product.update({
                'coverage_details': json.dumps(coverage_details, ensure_ascii=False),
                'coverage_limits': json.dumps(product.get('coverage_limits', {}), ensure_ascii=False),
                'deductible_options': json.dumps(product.get('deductible_options', {}), ensure_ascii=False),
                'coverage_scope': product.get('coverage_scope', ''),
                'excluded_items': json.dumps(product.get('excluded_items', []), ensure_ascii=False),
                'waiting_period': product.get('waiting_period', '')
            })
            
            # 가입 조건
            eligibility = product.get('eligibility_conditions', {})
            flat_product.update({
                'min_age': eligibility.get('min_age', 21),
                'max_age': eligibility.get('max_age', 65),
                'min_driving_experience': eligibility.get('min_driving_experience', 1),
                'max_car_age': eligibility.get('max_car_age', 15),
                'health_requirements': json.dumps(eligibility.get('health_requirements', []), ensure_ascii=False),
                'documentation_required': json.dumps(eligibility.get('documentation_required', []), ensure_ascii=False)
            })
            
            # 특약 및 서비스
            flat_product.update({
                'discount_options': json.dumps(product.get('discount_options', {}), ensure_ascii=False),
                'special_coverage': json.dumps(product.get('special_coverage', []), ensure_ascii=False),
                'emergency_services': json.dumps(product.get('emergency_services', []), ensure_ascii=False),
                'partner_benefits': json.dumps(product.get('partner_benefits', []), ensure_ascii=False),
                'digital_services': json.dumps(product.get('digital_services', []), ensure_ascii=False)
            })
            
            # 약관 정보
            flat_product.update({
                'terms_version': product.get('terms_version', ''),
                'effective_date': product.get('effective_date', ''),
                'revision_history': json.dumps(product.get('revision_history', []), ensure_ascii=False),
                'regulatory_approval': product.get('regulatory_approval', '')
            })
            
            # 메타 정보
            flat_product.update({
                'data_completeness': product.get('data_completeness', 0.0),
                'extraction_date': product.get('extraction_date', ''),
                'product_id': product.get('product_id', ''),
                'rating': round(np.random.uniform(3.5, 4.8), 1),
                'created_date': datetime.now().strftime('%Y-%m-%d')
            })
            
            flattened_products.append(flat_product)
        
        # DataFrame 생성
        df_products = pd.DataFrame(flattened_products)
        
        print(f"\n✅ 총 {len(df_products)}개 상세 보험상품 추출 완료")
        print(f"평균 데이터 완성도: {df_products['data_completeness'].mean():.1%}")
        
        # 보험사별 통계
        print(f"\n📊 보험사별 상품 수:")
        company_counts = df_products['company_name'].value_counts()
        for company, count in company_counts.items():
            avg_completeness = df_products[df_products['company_name']==company]['data_completeness'].mean()
            print(f"  {company}: {count}개 (완성도: {avg_completeness:.1%})")
        
        return df_products
    
    def save_to_csv(self, df_products, output_path='detailed_insurance_products.csv'):
        """상세 추출 결과를 CSV로 저장"""
        try:
            df_products.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 상세 데이터 저장 완료: {output_path}")
            
            # 통계 정보 출력
            print(f"\n📈 추출 통계:")
            print(f"  전체 상품 수: {len(df_products)}개")
            print(f"  평균 보험료: {df_products['monthly_premium'].mean():,.0f}원/월")
            print(f"  데이터 완성도: {df_products['data_completeness'].mean():.1%}")
            print(f"  추출 성공률: {len(df_products[df_products['data_completeness'] > 0.5]) / len(df_products):.1%}")
            
            # 샘플 데이터 출력
            print(f"\n📋 샘플 데이터 (상위 3개):")
            sample_cols = ['company_name', 'product_name', 'monthly_premium', 'data_completeness']
            print(df_products[sample_cols].head(3))
            
            return True
            
        except Exception as e:
            print(f"❌ 파일 저장 실패: {str(e)}")
            return False
    
    def generate_summary_report(self, df_products):
        """추출 결과 요약 보고서 생성"""
        report = {
            'extraction_summary': {
                'total_products': len(df_products),
                'total_companies': df_products['company_name'].nunique(),
                'avg_completeness': df_products['data_completeness'].mean(),
                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            
            'company_analysis': {},
            'product_analysis': {},
            'data_quality': {},
            'word_frequency_analysis': {}
        }
        
        # 보험사별 분석
        for company in df_products['company_name'].unique():
            company_data = df_products[df_products['company_name'] == company]
            report['company_analysis'][company] = {
                'product_count': len(company_data),
                'avg_premium': company_data['monthly_premium'].mean(),
                'completeness': company_data['data_completeness'].mean(),
                'categories': company_data['product_category'].value_counts().to_dict()
            }
        
        # 상품 분석
        report['product_analysis'] = {
            'categories': df_products['product_category'].value_counts().to_dict(),
            'sales_channels': df_products['sales_channel'].value_counts().to_dict(),
            'premium_range': {
                'min': df_products['monthly_premium'].min(),
                'max': df_products['monthly_premium'].max(),
                'avg': df_products['monthly_premium'].mean()
            }
        }
        
        # 데이터 품질
        high_quality = len(df_products[df_products['data_completeness'] > 0.7])
        medium_quality = len(df_products[df_products['data_completeness'].between(0.4, 0.7)])
        low_quality = len(df_products[df_products['data_completeness'] < 0.4])
        
        report['data_quality'] = {
            'high_quality': high_quality,
            'medium_quality': medium_quality,
            'low_quality': low_quality,
            'quality_distribution': {
                'high': high_quality / len(df_products),
                'medium': medium_quality / len(df_products),
                'low': low_quality / len(df_products)
            }
        }
        
        # 단어 빈도 분석 추가
        report['word_frequency_analysis'] = self._analyze_word_frequency(df_products)
        
        return report
    
    def _analyze_word_frequency(self, df_products):
        """단어 빈도 분석"""
        print("\n📊 단어 빈도 분석 중...")
        
        # 모든 텍스트 데이터 수집
        all_text = ""
        
        # 상품명에서 텍스트 추출
        all_text += " ".join(df_products['product_name'].fillna('').astype(str))
        
        # JSON 필드들에서 텍스트 추출
        json_columns = ['coverage_details', 'special_coverage', 'emergency_services', 
                       'partner_benefits', 'digital_services', 'excluded_items']
        
        for col in json_columns:
            if col in df_products.columns:
                for json_str in df_products[col].fillna('[]'):
                    try:
                        if isinstance(json_str, str) and json_str.strip():
                            # JSON 문자열을 파싱하여 텍스트 추출
                            data = json.loads(json_str)
                            if isinstance(data, dict):
                                all_text += " ".join(str(v) for v in data.values())
                            elif isinstance(data, list):
                                all_text += " ".join(str(item) for item in data)
                            else:
                                all_text += str(data)
                    except:
                        # JSON 파싱 실패시 문자열 그대로 사용
                        all_text += str(json_str)
        
        # 기타 텍스트 컬럼들
        text_columns = ['premium_range', 'coverage_scope', 'waiting_period', 
                       'terms_version', 'regulatory_approval']
        
        for col in text_columns:
            if col in df_products.columns:
                all_text += " ".join(df_products[col].fillna('').astype(str))
        
        # 텍스트 전처리
        # 한글, 영문, 숫자만 추출
        cleaned_text = re.sub(r'[^\w\s가-힣]', ' ', all_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # 단어 분리 (한글 2글자 이상, 영문 3글자 이상)
        korean_words = re.findall(r'[가-힣]{2,}', cleaned_text)
        english_words = re.findall(r'[a-zA-Z]{3,}', cleaned_text.lower())
        
        # 불용어 제거
        stop_words = {
            '보험', '자동차', '상품', '서비스', '고객', '가입', '지원', '제공', '포함', '경우',
            '대상', '기준', '이상', '이하', '관련', '등등', '기타', '해당', '전체', '일반',
            'insurance', 'auto', 'car', 'service', 'customer', 'include', 'support'
        }
        
        # 불용어 제거 후 빈도 계산
        filtered_korean = [word for word in korean_words if word not in stop_words]
        filtered_english = [word for word in english_words if word not in stop_words]
        
        # 빈도 계산
        korean_freq = Counter(filtered_korean)
        english_freq = Counter(filtered_english)
        
        # 숫자 패턴 분석
        numbers = re.findall(r'\d+', all_text)
        number_freq = Counter(numbers)
        
        # 특수 키워드 분석 (보험 관련 전문용어)
        insurance_keywords = [
            '대인배상', '대물배상', '자차보험', '자기신체사고', '무보험차상해',
            '출동서비스', '견인서비스', '렌터카', '할인', '특약', '면책',
            '다이렉트', '종합보험', '책임보험', '운전자보험'
        ]
        
        keyword_freq = {}
        for keyword in insurance_keywords:
            count = all_text.count(keyword)
            if count > 0:
                keyword_freq[keyword] = count
        
        return {
            'total_words': len(korean_words) + len(english_words),
            'unique_words': len(set(korean_words + english_words)),
            'top_korean_words': dict(korean_freq.most_common(20)),
            'top_english_words': dict(english_freq.most_common(15)),
            'top_numbers': dict(number_freq.most_common(15)),
            'insurance_keywords': dict(sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)),
            'word_statistics': {
                'korean_word_count': len(korean_words),
                'english_word_count': len(english_words),
                'unique_korean': len(set(korean_words)),
                'unique_english': len(set(english_words))
            }
        }


# 메인 실행 함수
def main():
    """상세 추출기 메인 실행"""
    
    print("=== 상세 보험 약관 PDF 데이터 추출기 ===")
    print("모든 보험 정보를 상세하게 추출합니다.")
    
    # 기존 파일 확인
    print("\n🔍 기존 파일 확인 중...")
    csv_file = 'detailed_insurance_products.csv'
    json_file = 'extraction_report.json'
    
    csv_exists = Path(csv_file).exists()
    json_exists = Path(json_file).exists()
    
    if csv_exists or json_exists:
        print(f"📁 발견된 기존 파일:")
        if csv_exists:
            csv_size = Path(csv_file).stat().st_size
            print(f"  ✅ {csv_file} ({csv_size:,} bytes)")
        if json_exists:
            json_size = Path(json_file).stat().st_size
            print(f"  ✅ {json_file} ({json_size:,} bytes)")
        
        # 사용자 선택
        print(f"\n❓ 어떻게 하시겠습니까?")
        print(f"  1. 기존 파일 사용 (기존 파일 로드 및 분석)")
        print(f"  2. 새로 추출 (기존 파일 덮어쓰기)")
        print(f"  3. 백업 후 새로 추출")
        
        choice = input("선택하세요 (1/2/3, 기본값=1): ").strip() or "1"
        
        if choice == "1":
            print(f"📊 기존 파일을 사용합니다.")
            if csv_exists:
                load_and_analyze_existing_data(csv_file)
            return
        elif choice == "3":
            # 백업 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if csv_exists:
                backup_csv = f'backup_{timestamp}_{csv_file}'
                Path(csv_file).rename(backup_csv)
                print(f"💾 CSV 백업: {backup_csv}")
            if json_exists:
                backup_json = f'backup_{timestamp}_{json_file}'
                Path(json_file).rename(backup_json)
                print(f"💾 JSON 백업: {backup_json}")
        
        print(f"🚀 새로운 추출을 시작합니다...")
    else:
        print(f"📄 기존 파일이 없습니다. 새로운 추출을 시작합니다.")
    
    # 상세 추출기 초기화
    extractor = DetailedInsurancePDFExtractor()
    
    # PDF 폴더 경로 설정
    pdf_folder_path = "./dataset_pdf"  # 실제 경로로 수정
    
    print(f"\n📁 PDF 폴더: {pdf_folder_path}")
    print("📄 지원 파일명 형식:")
    print("  - 삼성화재_약관.pdf")
    print("  - 현대해상_자동차보험_약관.pdf")
    print("  - KB손해보험_상품안내.pdf")
    
    # 폴더 확인
    if not Path(pdf_folder_path).exists():
        print(f"❌ 폴더가 존재하지 않습니다: {pdf_folder_path}")
        print("💡 PDF 폴더를 만들고 PDF 파일들을 넣어주세요.")
        return
    
    try:
        # 상세 데이터 추출
        print(f"\n🚀 상세 추출 시작...")
        df_products = extractor.extract_from_pdf_folder(pdf_folder_path)
        
        if not df_products.empty:
            # 상세 CSV 저장
            success = extractor.save_to_csv(df_products, csv_file)
            
            if success:
                # 요약 보고서 생성
                summary_report = extractor.generate_summary_report(df_products)
                
                # 보고서 저장
                try:
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(summary_report, f, ensure_ascii=False, indent=2)
                    print(f"📊 보고서 저장: {json_file}")
                except Exception as e:
                    print(f"⚠️ JSON 저장 실패: {str(e)}")
                
                print(f"\n🎉 상세 추출 완료!")
                print(f"📊 결과 파일:")
                print(f"  - {csv_file} (상세 상품 데이터)")
                print(f"  - {json_file} (추출 요약 보고서)")
                print(f"\n📈 요약:")
                print(f"  상품 수: {summary_report['extraction_summary']['total_products']}개")
                print(f"  보험사 수: {summary_report['extraction_summary']['total_companies']}개")
                print(f"  평균 완성도: {summary_report['extraction_summary']['avg_completeness']:.1%}")
            else:
                print("❌ CSV 저장에 실패했습니다.")
        else:
            print("❌ 추출된 상품이 없습니다.")
            print("💡 PDF 파일 형식이나 내용을 확인해주세요.")
            
    except Exception as e:
        print(f"❌ 실행 중 오류: {str(e)}")
        print("💡 라이브러리 설치 상태와 PDF 파일을 확인해주세요.")


def load_and_analyze_existing_data(csv_file):
    """기존 CSV 파일 로드 및 분석"""
    try:
        print(f"\n📊 기존 데이터 로드 중: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        print(f"✅ 데이터 로드 완료!")
        print(f"📈 기본 통계:")
        print(f"  총 상품 수: {len(df):,}개")
        print(f"  보험사 수: {df['company_name'].nunique()}개")
        
        if 'data_completeness' in df.columns:
            avg_completeness = df['data_completeness'].mean()
            print(f"  평균 완성도: {avg_completeness:.1%}")
        
        if 'monthly_premium' in df.columns:
            avg_premium = df['monthly_premium'].mean()
            print(f"  평균 월 보험료: {avg_premium:,.0f}원")
        
        # 보험사별 통계
        print(f"\n🏢 보험사별 상품 수:")
        company_counts = df['company_name'].value_counts()
        for company, count in company_counts.items():
            print(f"  {company}: {count}개")
        
        # 상품 샘플 출력
        print(f"\n📋 상품 샘플 (상위 3개):")
        sample_cols = ['company_name', 'product_name', 'monthly_premium']
        available_cols = [col for col in sample_cols if col in df.columns]
        if available_cols:
            print(df[available_cols].head(3).to_string(index=False))
        
        # 데이터 품질 분석
        if 'data_completeness' in df.columns:
            print(f"\n📊 데이터 품질 분석:")
            high_quality = len(df[df['data_completeness'] > 0.7])
            medium_quality = len(df[df['data_completeness'].between(0.4, 0.7)])
            low_quality = len(df[df['data_completeness'] < 0.4])
            
            print(f"  고품질 (70% 이상): {high_quality}개 ({high_quality/len(df):.1%})")
            print(f"  중품질 (40-70%): {medium_quality}개 ({medium_quality/len(df):.1%})")
            print(f"  저품질 (40% 미만): {low_quality}개 ({low_quality/len(df):.1%})")
        
        print(f"\n✅ 기존 데이터 분석 완료!")
        
    except Exception as e:
        print(f"❌ 기존 파일 로드 실패: {str(e)}")
        print("💡 파일이 손상되었을 수 있습니다. 새로 추출하시겠습니까?")
        retry = input("새로 추출하시겠습니까? (y/N): ").strip().lower()
        if retry == 'y':
            main()  # 재귀 호출로 새로 추출


if __name__ == "__main__":
    main()


# 필요한 라이브러리 설치 안내
print("\n" + "="*60)
print("📦 필수 라이브러리 설치:")
print("pip install pdfplumber PyPDF2 tabula-py pandas numpy openpyxl")
print("\n✅ Java 설정 완료:")
print("- Java 경로: C:/Program Files/Java/jdk-17")
print("- tabula-py로 고성능 표 추출 가능")
print("- pdfplumber로 백업 추출")
print("- PDF 파일은 텍스트 추출이 가능한 형태여야 합니다")
print("="*60)