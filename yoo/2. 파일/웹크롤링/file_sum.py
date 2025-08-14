from pathlib import Path
import pandas as pd
import re, unicodedata, locale

# =========================
# 경로 설정 (기존 경로 그대로)
# =========================
input_dir  = Path(r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\1.보험용어\1.원본")
output_dir = Path(r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\1.보험용어\2.변환본(가공,최종)")

# 새 폴더 생성하지 않음: 없으면 오류
if not input_dir.exists():
    raise SystemExit(f"[오류] 입력 폴더가 없습니다: {input_dir}")
if not output_dir.exists():
    raise SystemExit(f"[오류] 출력 폴더가 없습니다(자동 생성 안 함): {output_dir}")

# =========================
# 입력 CSV만 수집
# =========================
csv_files = [p for p in input_dir.glob("*") if p.is_file() and p.suffix.lower() == ".csv"]

print("발견 CSV 파일 수:", len(csv_files))
for i, p in enumerate(csv_files, 1):
    print(f"{i:2d}. {p.name}")

if not csv_files:
    raise SystemExit("읽어들인 CSV가 없습니다.")

# =========================
# 로드 & 병합
# =========================
dfs = []
for p in csv_files:
    df = None
    for enc in ("utf-8", "cp949"):  # 인코딩 폴백
        try:
            df = pd.read_csv(p, dtype=str, encoding=enc, engine="python")
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        print(f"[WARN] 인코딩 실패로 스킵: {p}")
        continue

    # 필요한 컬럼 보정
    for col in ["id", "term", "description", "source", "collected_date"]:
        if col not in df.columns:
            df[col] = ""
    dfs.append(df[["id", "term", "description", "source", "collected_date"]])

if not dfs:
    raise SystemExit("[오류] 읽을 수 있는 CSV가 없습니다.")

raw = pd.concat(dfs, ignore_index=True)
print("병합 후 총 행수:", len(raw))

# =========================
# 중복 정리
# - term+description 기준으로 1개만 남김 (요청안 유지)
#   만약 '중복 전체 삭제' 원하면 아래 drop_duplicates 대신 dup_mask 방식 사용
# =========================
clean = raw.drop_duplicates(subset=["term", "description"], keep="first").copy()
print("term+description 기준 1개만 남긴 행수:", len(clean))


import re, unicodedata, locale

# 1) 패턴 정의
HAN_BLOCKS = r"\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"  # CJK Ext-A, Unified, Compatibility
PAT_HAN_ENG = re.compile(f"[A-Za-z{HAN_BLOCKS}]+")       # 영문 + 한자 시퀀스
PAT_HAN_ENG_REMOVE = re.compile(f"[A-Za-z{HAN_BLOCKS}]") # 한 글자 단위 제거

def extract_han_eng_seq(text: str) -> str:
    if pd.isna(text):
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    parts = PAT_HAN_ENG.findall(s)
    return " ".join(parts)

def remove_han_eng(text: str) -> str:
    if pd.isna(text):
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = PAT_HAN_ENG_REMOVE.sub("", s)   # 영문·한자 제거
    s = re.sub(r"\s+", " ", s).strip()  # 공백 정리
    return s

# 2) 미리보기용 컬럼 구성
preview = clean.copy()
preview["term_orig"] = preview["term"]                         # 원본
preview["han_eng_found"] = preview["term_orig"].apply(extract_han_eng_seq)  # 검출
preview["term_clean"] = preview["term_orig"].apply(remove_han_eng)          # 정제

# 3) 정렬
def _try_set_korean_locale():
    for loc in ("ko_KR.UTF-8", "ko_KR.utf8", "Korean_Korea.949"):
        try:
            locale.setlocale(locale.LC_COLLATE, loc)
            return True
        except Exception:
            pass
    return False

if _try_set_korean_locale():
    preview = preview.sort_values(by="term_clean",
                                  key=lambda s: s.map(locale.strxfrm),
                                  kind="mergesort").reset_index(drop=True)
else:
    preview = preview.sort_values(by="term_clean", kind="mergesort").reset_index(drop=True)

# 4) 저장
cols = ["term_orig", "han_eng_found", "term_clean", "description", "source", "collected_date"]
out_path = output_dir / "terms_preview_full.csv"
preview.to_csv(out_path, index=False, encoding="utf-8-sig", columns=cols)
print("저장:", out_path)
