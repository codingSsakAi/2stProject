#!/usr/bin/env python
# C:\Users\Admin\Desktop\insurance_project\manage.py
import os
import sys
from pathlib import Path

def main():
    # 현재 실행 루트
    BASE_DIR = Path(__file__).resolve().parent

    # 1) 우리 루트를 sys.path 맨 앞에
    if str(BASE_DIR) in sys.path:
        sys.path.remove(str(BASE_DIR))
    sys.path.insert(0, str(BASE_DIR))

    # 2) 동일 이름 패키지를 가진 "다른 루트" 들은 목록의 뒤로 밀기
    #    (예: C:\ai_x\2ndProject\jang\insurance_project 같은 과거 경로)
    for p in list(sys.path):
        try:
            pp = Path(p)
            if pp == BASE_DIR:
                continue
            if (pp / "insurance_app").exists() and (pp / "insurance_project").exists():
                sys.path.remove(p)
                sys.path.append(p)  # ← 뒤로
        except Exception:
            pass

    # 3) 팀원 모듈(0826-5)이 현재 루트 아래 있으면 '뒤'에만 붙임
    extra = BASE_DIR / "0826-5"
    if extra.exists() and str(extra) not in sys.path:
        sys.path.append(str(extra))  # 맨 앞 금지

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "insurance_project.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django import 실패: 가상환경/설치 확인") from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
