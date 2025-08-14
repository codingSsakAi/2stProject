# insurance_portal/utils/loaders.py
# 기능: 앱 패키지(insurance_portal) 내부 data/ 폴더에서 JSON/텍스트 리소스를 안전하게 로드
# 특징:
#  - importlib.resources를 사용하여 패키지 내부 리소스를 경로 하드코딩 없이 읽습니다.
#  - lru_cache로 동일 파일 재요청 시 디스크 I/O를 최소화합니다.
#  - 파일 누락/파싱 오류 시 명확한 예외를 발생시켜 상위에서 처리하기 쉽게 합니다.

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources


class DataLoadError(RuntimeError):
    """데이터 파일 읽기 실패 시 발생하는 예외."""
    pass


def _open_resource(package: str, filename: str):
    """
    내부 사용: 패키지 리소스를 열어 file-like 객체를 반환.
    - package: "insurance_portal.data" 형태의 패키지 경로
    - filename: 예) "weekly_articles.json"
    """
    try:
        return resources.files(package).joinpath(filename).open("r", encoding="utf-8")
    except FileNotFoundError as e:
        raise DataLoadError(f"리소스 파일을 찾을 수 없습니다: {package}/{filename}") from e
    except Exception as e:
        raise DataLoadError(f"리소스 파일을 여는 중 오류: {package}/{filename} ({e})") from e


@lru_cache(maxsize=32)
def load_json(filename: str):
    """
    insurance_portal/data/<filename>에서 JSON을 로드하여 Python 객체(dict/list)로 반환.
    - 캐시됨: 동일 파일에 대한 반복 접근 시 디스크 I/O 최소화.
    - 예외: 파일 누락/파싱 오류 시 DataLoadError 발생.
    사용 예) items = load_json("weekly_articles.json")
    """
    package = "insurance_portal.data"
    try:
        with _open_resource(package, filename) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise DataLoadError(f"JSON 파싱 오류: {package}/{filename} (line {e.lineno}, col {e.colno})") from e


@lru_cache(maxsize=32)
def load_text(filename: str) -> str:
    """
    insurance_portal/data/<filename>에서 텍스트 파일을 로드하여 문자열로 반환.
    - 캐시됨: 동일 파일 반복 접근 시 I/O 최소화.
    사용 예) md = load_text("note.md")
    """
    package = "insurance_portal.data"
    with _open_resource(package, filename) as f:
        return f.read()
