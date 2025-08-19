# CSV to CSV Converter for Chatbot Data
# 목적: 웹 챗봇용 데이터를 CSV에서 3개의 CSV 파일로 변환
# _cleaned.csv: 최종 데이터 (term, description만)
# _removed.csv: 삭제된 데이터 로그  
# _original.csv: 원본 데이터

import pandas as pd
from pathlib import Path
import re

# ====================== 설정 ======================
# 파일 경로 설정
INPUT_CSV_PATH = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\2-1.과실비율 용어\1.원본\과실비율정보포털_과실비율 용어해설(61개).csv"
OUTPUT_BASE_PATH = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\2-1.과실비율 용어\2.변환본(가공,최종)\과실비율_용어해설(61개)_0819"

# 인코딩 설정 (한글 파일이면 보통 cp949)
ENCODING = "utf-8"  # utf-8에서 오류 나면 cp949로 시도

# 제거할 키워드 설정 (옵션)
REMOVE_KEYWORDS = [
    "test",
    # "예시"
]

# ====================== 함수 정의 ======================

def clean_text(text):
    """텍스트 기본 정제"""
    if not isinstance(text, str):
        return ""
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    # 연속된 공백을 하나로 변경
    text = re.sub(r'\s+', ' ', text)
    
    return text

def should_remove_row(term, description, keywords):
    """행 삭제 여부 판단"""
    if not keywords:
        return False
    
    text_to_check = f"{term} {description}".lower()
    
    for keyword in keywords:
        if keyword.lower() in text_to_check:
            return True
    
    return False

def process_csv_to_csv(input_path, output_base_path, encoding="cp949", remove_keywords=None):
    """CSV를 3개의 CSV 파일로 변환하는 메인 함수"""
    
    if remove_keywords is None:
        remove_keywords = []
    
    print("🚀 CSV 변환 시작...")
    
    # 1. CSV 파일 읽기
    try:
        df_original = pd.read_csv(input_path, encoding=encoding)
        print(f"✓ CSV 파일 읽기 완료: {len(df_original)}행")
        print(f"✓ 컬럼: {list(df_original.columns)}")
    except UnicodeDecodeError:
        print(f"❌ 인코딩 오류. {encoding} 대신 다른 인코딩을 시도하세요.")
        print("💡 시도해볼 인코딩: utf-8, cp949, euc-kr")
        return
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        return
    
    # 2. 필수 컬럼 확인
    required_columns = ['term', 'description']
    missing_columns = [col for col in required_columns if col not in df_original.columns]
    
    if missing_columns:
        print(f"❌ 필수 컬럼이 없습니다: {missing_columns}")
        print(f"현재 컬럼: {list(df_original.columns)}")
        return
    
    # 3. 데이터 정제 및 필터링
    print("🔄 데이터 정제 중...")
    cleaned_data = []
    removed_data = []
    
    for idx, row in df_original.iterrows():
        term = clean_text(str(row.get('term', '')))
        description = clean_text(str(row.get('description', '')))
        
        # 빈 데이터 체크
        if not term or not description:
            removed_data.append({
                'original_index': idx,
                'term': term,
                'description': description,
                'remove_reason': '빈 데이터',
                'source': row.get('source', ''),
                'collected_date': row.get('collected_date', '')
            })
            continue
        
        # 키워드 기반 제거 체크
        if should_remove_row(term, description, remove_keywords):
            removed_data.append({
                'original_index': idx,
                'term': term,
                'description': description,
                'remove_reason': f'키워드 포함: {remove_keywords}',
                'source': row.get('source', ''),
                'collected_date': row.get('collected_date', '')
            })
            continue
        
        # 유효한 데이터
        cleaned_data.append({
            'term': term,
            'description': description
        })
    
    # 4. DataFrame 생성
    df_cleaned = pd.DataFrame(cleaned_data)
    df_removed = pd.DataFrame(removed_data)
    
    # 5. 출력 경로 설정
    output_base = Path(output_base_path)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    
    cleaned_path = f"{output_base}_cleaned.csv"
    removed_path = f"{output_base}_removed.csv"
    original_path = f"{output_base}_original.csv"
    
    # 6. CSV 파일들로 저장
    print("💾 파일 저장 중...")
    try:
        # 최종 정제된 데이터 (term, description만)
        df_cleaned.to_csv(cleaned_path, index=False, encoding=encoding)
        
        # 삭제된 데이터 로그
        df_removed.to_csv(removed_path, index=False, encoding=encoding)
        
        # 원본 데이터 백업
        df_original.to_csv(original_path, index=False, encoding=encoding)
        
        print("✅ 모든 파일이 성공적으로 저장되었습니다!")
        
    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")
        return
    
    # 7. 결과 출력
    print("\n" + "="*50)
    print("🎉 처리 완료!")
    print("="*50)
    print(f"📊 원본 데이터: {len(df_original)}행")
    print(f"✅ 최종 데이터: {len(df_cleaned)}행")
    print(f"🗑️ 삭제된 데이터: {len(df_removed)}행")
    
    print(f"\n📁 생성된 파일들:")
    print(f"   🎯 최종 데이터 (챗봇용): {cleaned_path}")
    print(f"   📋 삭제 로그: {removed_path}")
    print(f"   💾 원본 백업: {original_path}")
    
    # 삭제 사유별 통계
    if not df_removed.empty:
        print(f"\n📈 삭제 사유별 통계:")
        remove_stats = df_removed['remove_reason'].value_counts()
        for reason, count in remove_stats.items():
            print(f"   - {reason}: {count}행")
    
    print(f"\n💡 웹 챗봇에서는 '{cleaned_path}' 파일을 사용하세요!")
    
    return df_cleaned, df_removed, df_original

# ====================== 실행 ======================

def main():
    """메인 실행 함수"""
    
    print("🤖 웹 챗봇용 CSV 데이터 변환기")
    print("="*50)
    
    # 파일 경로 확인
    input_file = Path(INPUT_CSV_PATH)
    if not input_file.exists():
        print(f"❌ 입력 파일이 없습니다:")
        print(f"   {INPUT_CSV_PATH}")
        print("\n💡 INPUT_CSV_PATH를 올바른 경로로 수정하세요.")
        return
    
    print(f"📂 입력 파일: {input_file.name}")
    print(f"📤 출력 경로: {OUTPUT_BASE_PATH}")
    
    # 변환 실행
    result = process_csv_to_csv(
        input_path=INPUT_CSV_PATH,
        output_base_path=OUTPUT_BASE_PATH,
        encoding=ENCODING,
        remove_keywords=REMOVE_KEYWORDS
    )
    
    if result:
        print("\n🎊 변환이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()