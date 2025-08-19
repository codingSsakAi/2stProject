# file: insurance_terms_3sheets.py
# 목적:
#  - 입력 CSV 1개를 읽어 엑셀(xlsx) 3시트로 저장
#    시트1 cleaned : 원본을 복사한 뒤 정제 수행, 마지막에 A,B(원본/삭제텍스트) 컬럼 제거
#    시트2 removed : 삭제된 "행" + 삭제된 "텍스트 조각" 로그
#    시트3 original: 입력 CSV 그대로
#
# 사용 전 설정:
#  - INPUT_CSV_PATH, OUTPUT_XLSX_PATH, ENCODING, ROW_BLOCKLIST_KEYWORDS 수정
#
# 주의:
#  - pandas, xlsxwriter 필요: pip install pandas xlsxwriter

import re
from pathlib import Path
import pandas as pd

# ====================== 설정 ======================
# 1) 입력/출력 경로(고정)
INPUT_CSV_PATH  = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\1.보험용어\2.변환본(가공,최종)\보험용어 취합본(정리중_취합완료_0814_3).csv"
OUTPUT_XLSX_PATH = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\1.보험용어\2.변환본(가공,최종)\보험용어_정제_3시트_0819.xlsx"

# 2) 인코딩(국내 자료면 cp949일 수도 있음)
ENCODING = "utf-8"  # 필요시 "cp949"

# 3) 행 삭제 키워드(원하는 단어를 추가)
#    term_orig 또는 description에 아래 키워드가 하나라도 포함되면
#    해당 "행" 전체가 시트2(removed)로 이동되고 시트1에서는 제거
ROW_BLOCKLIST_KEYWORDS = [
    "골프","홀인원","건설","침몰","가스","연금","생명보험",
    "해상","주식","간병","요양","간성뇌증","개발","재무"
    "치매","건강진단","건물","건설","선박","건축가","화재","양성","악성",
    "종양","화물","경비","배당","고가품","고령","고용","석탄","치아","보철물","농사",
    "공기계","종업원","공동해손","공제","퇴직","교육","구조수색","여행","항공","국민생명",
    "회계","근로자","운송","수송","농기계","기업보험","기업","기왕령","심장","뇌혈관","고혈압",
    "시멘트","노동","냉동","냉장", "노인","상조","노후","농협","소아암","해손",
    "저축","단체","토목","빌딩","동물","관세","수입","수출","렌즈","방화","휴업",
    "휴대품","활어차","항로","기관지","천식","한글용어","학생종합","학생","교사",
    "페이퍼컴퍼니","임신","림프절","림프","암","크로스보더","카드보험","콘크리트","컴퓨터","영미법",
    "카메라","치주","치은","치관","잇몸","치근","염증","치주질환","추심","척추","처방","질멜","질권",
    "진사","적하","증가액","종합소득세","담보","종신","조직유도","기술보험","조정보험","철근","벽돌",
    "제세액","공보험","청약","부양","전업","전속","전문인","체류","회사","불법행위","공구","재고",
    "자유요율","보증보험","이익수수료","의사","의료사고","원천징수","원자력보험","원스톱","원수",
    "영국","요트","에치","엔터프라이즈아키텍처","에프","에디슨병","업무용 ","업무용",
    "어카운트 이어 베이시스","어린이12대다발성질병","액트 오브 갓","알바트로스비용","아말감",
    "실질적 감독주의","신생아","식물인간","식도","시력","승환계약","톤수","수재","수하인","수련시설",
    "손해사정","소훼","생활질환","생활설계","생활비","제조","판매업자","사태","사회보험",
    "근거법령(보험업감독업무시행세칙)","농어업인","녹내장","네임","","",""
    
    # 예시) "연금", "암보험", "질병후유장해"
    # 사용 시 소문자 비교이므로 한글/영문 그대로 넣어도 됩니다.
]

# 4) 최종 시트1에서 남길 컬럼
#    요구사항: 최종텍스트만 남기고 A,B(원본/삭제텍스트) 삭제
#    하지만 실무상 description/source/collected_date는 유지 권장 → 아래처럼 둠
FINAL_SHEET1_COLUMNS = ["term_clean", "description", "collected_date"]

# ================== 정규식/규칙 정의 ==================
HANGUL = r"\uAC00-\uD7A3"
HANJA  = r"\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"

# 한글-1) 괄호 안에 '한글'포함 -> 괄호 포함 전체 삭제 
rx_paren_with_hangul = re.compile(
    rf"\(([^)]*[{HANGUL}][^)]*)\)"
)

# 한글-2) 닫히지 않은 괄호 + '한글' 포함 → 여는 괄호부터 줄 끝까지 삭제
# 예: "(자동 갱신"
rx_open_paren_hangul_to_eol = re.compile(
    rf"\([^)]*[{HANGUL}][^)]*$"
)

# 영어-1) 한글 직후의 (english) → 괄호 포함 삭제 (영어 단독 용어는 유지)
rx_ko_then_paren_english = re.compile(
    rf"(?<=[{HANGUL}])\s*\(([A-Za-z][^)]*)\)"
)

# 영어-2) [영 : GIC] → 대괄호 블록 전체 삭제
rx_square_eng_block = re.compile(
    r"\[\s*영\s*:\s*[^]]*\]"
)

# 영어-3) /english → 슬래시 포함 오른쪽 영어 구간 삭제
rx_slash_english_to_eol = re.compile(
    r"\s*/\s*['']?[A-Za-z][A-Za-z0-9''\s\-\.,]*"
)

# 영어-4) '한글 바로 뒤에 붙은' 영어 런 전부 삭제
# 예: "가계약binder" , "만기연령maturity age, age at exit"
# FEOL(...) 단독 영문 약어는 유지됨(앞에 한글이 없어 매치 안 됨)
rx_ko_adjacent_english_right = re.compile(
    rf"(?<=[{HANGUL}])"                 # 직전이 한글이면
    r"[A-Za-z][A-Za-z0-9''\-]*"         # 영문 토큰 시작
    r"(?:\([^)]+\))?"                   # 뒤에 괄호-설명 붙으면 같이
    r"(?:[ \t,;:\-]+[A-Za-z][A-Za-z0-9''\-]*(?:\([^)]+\))?)*"  # 이어지는 영문 구절
)

# 한자-1) ( … ) 내부에 '한자' 1자 이상 포함 → 괄호 포함 삭제
rx_paren_with_hanja = re.compile(
    rf"\(([^)]*[{HANJA}][^)]*)\)"
)

# 한자-2a) / ... / 블록에 한자 포함 → 양쪽 슬래시 포함 통삭제
rx_slash_block_with_hanja = re.compile(
    rf"\s*/[^/]*[{HANJA}][^/]*/\s*"
)

# 한자-2b) '/한자...' 닫는 슬래시 없이 끝나는 경우 → 슬래시부터 행 끝까지 삭제
rx_slash_hanja_to_eol = re.compile(
    rf"\s*/\s*[{HANJA}][^\n\r]*"
)

# 닫히지 않은 괄호 + '한자' 포함 → 여는 괄호부터 줄 끝까지 삭제
# 예: "(個人用" , "(使用後 申告制 "
rx_open_paren_hanja_to_eol = re.compile(
    rf"\([^)]*[{HANJA}][^)]*$"
)

# 행 끝의 외딴 슬래시 제거(예: " ... /" → "")
rx_trailing_slash_ws = re.compile(r"\s*/\s*$")

# 공백에 둘러싸인 이중 슬래시 블록 제거(예: " / / " → 공백 1개)
rx_double_slash_ws = re.compile(r"\s*/\s*/\s*")

# 공백 정규화
rx_spaces = re.compile(r"\s+")

def apply_and_log(pattern, text, rule_name, removals):
    """패턴 일치 구간을 제거하며 removals에 로그를 쌓음."""
    def repl(m):
        s = m.group(0)
        removals.append({"rule": rule_name, "removed_text": s})
        return ""
    new_text, _ = pattern.subn(repl, text)
    return new_text

def apply_and_log_paren_inner(pattern, text, rule_name, removals):
    """괄호 포함 삭제. 로그에는 전체 블록을 기록."""
    def repl(m):
        whole = m.group(0)
        removals.append({"rule": rule_name, "removed_text": whole})
        return ""
    new_text, _ = pattern.subn(repl, text)
    return new_text

def apply_and_log_to_space(pattern, text, rule_name, removals):
    """매치 구간을 '공백 1개'로 치환하면서 로그에 남긴다."""
    def repl(m):
        removals.append({"rule": rule_name, "removed_text": m.group(0)})
        return " "
    new_text, _ = pattern.subn(repl, text)
    return new_text

# 어떤 키워드로 삭제되었는지 체크하는 함수
def find_block_keywords_in(text: str):
    """ROW_BLOCKLIST_KEYWORDS 중 text에 실제로 매칭된 키워드 리스트를 반환(대소문자 무시)."""
    if not ROW_BLOCKLIST_KEYWORDS or not isinstance(text, str):
        return []
    hits = []
    for kw in ROW_BLOCKLIST_KEYWORDS:
        if not kw:
            continue
        if re.search(re.escape(kw), text, flags=re.IGNORECASE):
            hits.append(kw)
    return hits

def cleanse_term(term_orig: str):
    """
    한 행의 term_orig를 규칙에 따라 정제하고,
    삭제된 조각 리스트(removals)를 함께 반환.
    """
    if not isinstance(term_orig, str):
        return term_orig, []

    s = term_orig
    removals = []

    # 1) [영 : ...] 블록
    s = apply_and_log(rx_square_eng_block, s, "square_eng_block", removals)

    # 2) (한자 포함) 닫힌 괄호
    s = apply_and_log_paren_inner(rx_paren_with_hanja, s, "paren_hanja", removals)

    # 3) (한글 포함) 닫힌 괄호  ← 추가 (예: (자동), (구 급부))
    s = apply_and_log_paren_inner(rx_paren_with_hangul, s, "paren_hangul", removals)

    # 4) 닫히지 않은 괄호 + 한자 → 여는 괄호부터 EOL 삭제  ← 추가
    s = apply_and_log(rx_open_paren_hanja_to_eol, s, "open_paren_hanja_to_eol", removals)

    # 5) 닫히지 않은 괄호 + 한글 → 여는 괄호부터 EOL 삭제  ← 추가
    s = apply_and_log(rx_open_paren_hangul_to_eol, s, "open_paren_hangul_to_eol", removals)

    # 6) 한글 바로 뒤의 (english)  ← 기존
    s = apply_and_log_paren_inner(rx_ko_then_paren_english, s, "paren_english_after_korean", removals)

    # 7) /.../ 블록 내 한자 포함 → 양 슬래시 포함 삭제  ← 기존
    s = apply_and_log(rx_slash_block_with_hanja, s, "slash_block_hanja", removals)

    # 8) /english → 슬래시 포함 오른쪽 영문 구간 삭제  ← 수정(따옴표 허용)
    s = apply_and_log(rx_slash_english_to_eol, s, "slash_english_to_eol", removals)

    # 9) '/한자...' (닫는 / 없음) → 슬래시부터 EOL 삭제  ← 기존
    s = apply_and_log(rx_slash_hanja_to_eol, s, "slash_hanja_to_eol", removals)

    # 10) 한글 바로 옆에 붙은 영문 런 통삭제  ← 추가
    s = apply_and_log(rx_ko_adjacent_english_right, s, "ko_adjacent_english_right", removals)

    # 11) " / / " 같은 이중 슬래시 뭉치 정리(공백 1개로 대체)  ← 추가
    s = apply_and_log_to_space(rx_double_slash_ws, s, "double_slash_ws", removals)

    # 12) 행 끝의 외딴 슬래시 제거  ← 추가
    s = apply_and_log(rx_trailing_slash_ws, s, "trailing_slash_ws", removals)

    # 마무리: 공백 압축
    s = rx_spaces.sub(" ", s).strip()

    return s, removals


def contains_block_keyword(text: str) -> bool:
    """행 삭제 키워드 포함 여부 판단."""
    if not ROW_BLOCKLIST_KEYWORDS:
        return False
    if not isinstance(text, str):
        return False
    t = text.lower()
    for kw in ROW_BLOCKLIST_KEYWORDS:
        if kw and kw.lower() in t:
            return True
    return False

def ensure_columns(df: pd.DataFrame):
    """필수 컬럼 기본 보정."""
    for col in ["term_orig", "description", "collected_date"]:
        if col not in df.columns:
            df[col] = ""
    return df

def main():
    inp = Path(INPUT_CSV_PATH)
    outp = Path(OUTPUT_XLSX_PATH)
    outp.parent.mkdir(parents=True, exist_ok=True)

    # 0) 원본 로드
    try:
        df_orig = pd.read_csv(inp, encoding=ENCODING)
    except UnicodeDecodeError:
        raise RuntimeError("인코딩 오류입니다. ENCODING 값을 'cp949' 등으로 변경 후 다시 실행하세요.")

    # 시트3(original): 입력 그대로
    original_df = df_orig.copy()

    # 시트1 작업용: 원본 복사 후 필수 컬럼 보정
    cleaned_work_df = ensure_columns(df_orig.copy())

    # 시트2 로그 누적
    removed_logs = []

    kept_rows = []
    for idx, row in cleaned_work_df.iterrows():
        term_orig = row.get("term_orig", "")
        desc      = row.get("description", "")
        source    = row.get("source", "")
        collected = row.get("collected_date", "")

        # 1) 행 삭제(키워드): 실제로 매칭된 키워드만 추출
        kw_orig = find_block_keywords_in(term_orig)
        kw_desc = find_block_keywords_in(desc)
        # 중복 제거하며 순서 보존
        seen = set()
        matched = []
        for k in kw_orig + kw_desc:
            if k not in seen:
                seen.add(k)
                matched.append(k)

        if matched:
            removed_logs.append({
                "row_id": idx,
                "source": source,
                "rule": "row_removed_by_keyword",
                # 실제 매칭된 키워드만 기록
                "removed_text": "; ".join(matched),
                "term_orig": term_orig,
                "han_eng_found": "",
                "term_clean": "",
                "description": desc,
                "collected_date": collected,
                # 참고용 필드(없어도 됨)
                "kept_row_id": None,
                "kept_description": None,
            })
            continue

        # 2) 텍스트 정제
        term_clean, removals = cleanse_term(str(term_orig) if pd.notna(term_orig) else "")
        han_eng_found = "; ".join([r["removed_text"] for r in removals]) if removals else ""

        # 삭제 조각 로그(행은 유지)
        for r in removals:
            removed_logs.append({
                "row_id": idx,
                "source": source,
                "rule": r["rule"],
                "removed_text": r["removed_text"],
                "term_orig": term_orig,
                "han_eng_found": han_eng_found,
                "term_clean": term_clean,
                "description": desc,
                "collected_date": collected,
                "kept_row_id": None,
                "kept_description": None,
            })

        kept_rows.append({
            "row_id": idx,  # 병합 로깅에 활용
            "term_orig": term_orig,
            "han_eng_found": han_eng_found,
            "term_clean": term_clean,
            "description": desc,
            "source": source,
            "collected_date": collected
        })

    # 시트1 중간 프레임
    cleaned_df_mid = pd.DataFrame(kept_rows, columns=[
        "row_id", "term_orig", "han_eng_found", "term_clean", "description", "source", "collected_date"
    ])

    # 3) 같은 term_clean 내 중복 처리
    #    - 동일 설명(문자 그대로 완전 동일): 1개만 남기고 나머지 시트2 이동(rule=dup_exact_same_desc)
    #    - 서로 다른 설명: 가장 긴 설명만 남기고 나머지는 시트2 이동(rule=merged_diff_desc)
    if not cleaned_df_mid.empty:
        keep_mask = pd.Series(True, index=cleaned_df_mid.index)

        for term, grp in cleaned_df_mid.groupby("term_clean", dropna=False, sort=False):
            if grp.shape[0] == 1:
                continue

            # desc 문자열 기준으로 첫 등장 인덱스 기억(완전 동일 판정)
            first_by_desc = {}
            unique_firsts = []  # (idx, desc) - 서로 다른 설명의 첫 등장만
            for i, r in grp.iterrows():
                d = r.get("description", "")
                if d in first_by_desc:
                    kept_i = first_by_desc[d]
                    # 동일 설명 중복 → 제거
                    if keep_mask.get(i, False):
                        keep_mask.at[i] = False
                        removed_logs.append({
                            "row_id": i,
                            "source": r.get("source", ""),
                            "rule": "dup_exact_same_desc",
                            "removed_text": "",
                            "term_orig": r.get("term_orig", ""),
                            "han_eng_found": r.get("han_eng_found", ""),
                            "term_clean": r.get("term_clean", ""),
                            "description": d,
                            "collected_date": r.get("collected_date", ""),
                            "kept_row_id": kept_i,
                            "kept_description": cleaned_df_mid.loc[kept_i, "description"],
                        })
                else:
                    first_by_desc[d] = i
                    unique_firsts.append((i, d))

            # 서로 다른 설명이 2개 이상이면 가장 긴 설명만 남기기
            if len(unique_firsts) >= 2:
                base_i, _ = unique_firsts[0]
                # 가장 긴 설명 찾기(빈 설명은 제외)
                merged_descs = [d for _, d in unique_firsts if isinstance(d, str) and d.strip() != ""]
                longest_desc = max(merged_descs, key=len)

                # base 행의 description을 가장 긴 텍스트로 교체
                cleaned_df_mid.at[base_i, "description"] = longest_desc

                # 나머지 유니크 첫 등장들은 제거하면서 로그 남김
                for i, d in unique_firsts[1:]:
                    if keep_mask.get(i, False):
                        keep_mask.at[i] = False
                        rr = cleaned_df_mid.loc[i]
                        removed_logs.append({
                            "row_id": i,
                            "source": rr.get("source", ""),
                            "rule": "merged_diff_desc",
                            "removed_text": d,  # 병합으로 제외된 설명 원문
                            "term_orig": rr.get("term_orig", ""),
                            "han_eng_found": rr.get("han_eng_found", ""),
                            "term_clean": rr.get("term_clean", ""),
                            "description": d,
                            "collected_date": rr.get("collected_date", ""),
                            "kept_row_id": base_i,
                            "kept_description": longest_desc,
                        })

        cleaned_df_mid = cleaned_df_mid.loc[keep_mask].copy()

    # 4) 시트1 최종: A,B 컬럼 + source 삭제
    cleaned_final_df = cleaned_df_mid.copy()
    for col_to_drop in ["term_orig", "han_eng_found", "source"]:
        if col_to_drop in cleaned_final_df.columns:
            cleaned_final_df.drop(columns=[col_to_drop], inplace=True)

    # 남길 컬럼 순서 정렬(설정값 기반)
    cols_exist = [c for c in FINAL_SHEET1_COLUMNS if c in cleaned_final_df.columns]
    cleaned_final_df = cleaned_final_df[cols_exist]

    # 5) 시트2 프레임
    removed_df = pd.DataFrame(removed_logs, columns=[
        "row_id", "source", "rule", "removed_text",
        "term_orig", "han_eng_found", "term_clean", "description", "collected_date",
        "kept_row_id", "kept_description"  # 중복/병합 로깅용
    ])

    # 6) 엑셀 저장: cleaned → removed → original
    with pd.ExcelWriter(outp, engine="xlsxwriter") as xw:
        cleaned_final_df.to_excel(xw, index=False, sheet_name="cleaned")
        removed_df.to_excel(xw, index=False, sheet_name="removed")
        original_df.to_excel(xw, index=False, sheet_name="original")

    # 요약
    print("=== Summary ===")
    print(f"Input rows          : {len(df_orig)}")
    print(f"Kept in cleaned     : {len(cleaned_final_df)}")
    print(f"Removed log entries : {len(removed_df)}")
    print(f"Output written to   : {outp}")


if __name__ == "__main__":
    main()