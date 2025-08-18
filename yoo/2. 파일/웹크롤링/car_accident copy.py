# -*- coding: utf-8 -*-
"""
교통사고 신속처리 표준 협의서 - 3페이지 자동기입 (구역상대 좌표 방식)
- 원본 PDF(5장)에서 3페이지만 분리 → 구역별(T/A/B/C/D/E) 상대좌표로 텍스트/체크/원표시 렌더 → 1장 PDF 생성
- 좌표계: PyMuPDF (0,0) = 좌상단, x→오른쪽, y→아래
- 한글 폰트: 시스템 폰트 파일 경로를 지정 (예: 맑은고딕)
"""

from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF

# ====== 사용자 설정 ======
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"   # Windows 예시 (macOS는 /System/Library/Fonts/AppleGothic.ttf 등)
FONT_NAME = "KFONT"
FONT_SIZE = 10
CHECK_SIZE = 12
CHECK_MARK = "✔"
# ========================


# ------------------------
# 유틸: 3페이지만 추출
# ------------------------
def extract_page3(src_pdf: str, dst_pdf: str) -> None:
    """원본 PDF에서 3페이지만 추출해 단일 1페이지 PDF로 저장"""
    src = fitz.open(src_pdf)
    if src.page_count < 3:
        src.close()
        raise ValueError("PDF에 3페이지가 없습니다.")
    out = fitz.open()
    out.insert_pdf(src, from_page=2, to_page=2)  # index=2 -> 3페이지
    out.save(dst_pdf, deflate=True)
    out.close()
    src.close()


# ------------------------
# 보정용 그리드 PDF 생성
# ------------------------
def draw_grid_for_calibration(pdf_path: str, out_path: str, step: int = 50) -> None:
    """좌표 보정용 그리드/눈금 오버레이를 추가한 복사본 생성"""
    doc = fitz.open(pdf_path)
    page = doc[0]
    w, h = page.rect.width, page.rect.height

    shape = page.new_shape()
    # 세로선
    x = 0
    while x <= w:
        shape.draw_line(fitz.Point(x, 0), fitz.Point(x, h))
        x += step
    # 가로선
    y = 0
    while y <= h:
        shape.draw_line(fitz.Point(0, y), fitz.Point(w, y))
        y += step

    shape.finish(color=(0.7, 0.7, 0.7), width=0.3)
    shape.commit()

    # 좌표 라벨
    page.insert_font(fontname=FONT_NAME, fontfile=FONT_PATH)
    for gx in range(0, int(w) + 1, step):
        page.insert_text(fitz.Point(gx + 2, 12), f"x={gx}",
                        fontname=FONT_NAME, fontsize=6, color=(0, 0, 0))
    for gy in range(0, int(h) + 1, step):
        page.insert_text(fitz.Point(2, gy + 10), f"y={gy}",
                        fontname=FONT_NAME, fontsize=6, color=(0, 0, 0))

    doc.save(out_path, deflate=True)
    doc.close()


# ------------------------
# 기본 드로잉 함수
# ------------------------
def insert_text(page: fitz.Page, x: float, y: float, text: str,
                font: str = FONT_NAME, size: int = FONT_SIZE) -> None:
    page.insert_text(fitz.Point(x, y), text, fontname=font, fontsize=size, color=(0, 0, 0))


def draw_checkbox(page: fitz.Page, x: float, y: float, checked: bool,
                  box: int = CHECK_SIZE, font: str = FONT_NAME,
                  style: str = "check", line_w: float = 0.8) -> None:
    """
    style:
      - "check": 네모 + ✔ 문자
      - "x"    : 네모 + 대각선 X
      - "fill" : 네모 채움(■)
    """
    rect = fitz.Rect(x, y, x + box, y + box)
    page.draw_rect(rect, color=(0, 0, 0), width=line_w)
    if not checked:
        return

    if style == "check":
        page.insert_text(fitz.Point(x + 2, y + box - 2), CHECK_MARK,
                        fontname=font, fontsize=box - 2, color=(0, 0, 0))
    elif style == "x":
        page.draw_line(fitz.Point(x + 1, y + 1), fitz.Point(x + box - 1, y + box - 1),
                      color=(0, 0, 0), width=line_w)
        page.draw_line(fitz.Point(x + box - 1, y + 1), fitz.Point(x + 1, y + box - 1),
                      color=(0, 0, 0), width=line_w)
    elif style == "fill":
        page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))


def draw_circle_mark(page: fitz.Page, cx: float, cy: float, r: float,
                    checked: bool = True, mode: str = "ring",
                    line_w: float = 0.8) -> None:
    """
    mode:
      - ring : 빈 원(O) 테두리만
      - dot  : 가운데 점만 ●
      - radio: 테두리 + 가운데 작은 점(라디오버튼)
    """
    if hasattr(page, "draw_circle"):
        page.draw_circle(center=fitz.Point(cx, cy), radius=r,
                        color=(0, 0, 0), width=line_w)
    else:
        rect = fitz.Rect(cx - r, cy - r, cx + r, cy + r)
        page.draw_oval(rect, color=(0, 0, 0), width=line_w)

    if not checked:
        return

    if mode in ("dot", "radio"):
        r2 = max(1, r * 0.45)
        if hasattr(page, "draw_circle"):
            page.draw_circle(center=fitz.Point(cx, cy), radius=r2,
                            color=(0, 0, 0), fill=(0, 0, 0))
        else:
            rect2 = fitz.Rect(cx - r2, cy - r2, cx + r2, cy + r2)
            page.draw_oval(rect2, color=(0, 0, 0), fill=(0, 0, 0))


# ------------------------
# 구역상대 좌표 렌더링
# ------------------------
def _rel_to_abs(zone_rect: Tuple[float, float, float, float],
                rx: float, ry: float) -> Tuple[float, float]:
    zx, zy, zw, zh = zone_rect
    return zx + rx * zw, zy + ry * zh


def fill_page3_grouped(src_page3_pdf: str, out_pdf: str,
                      payload: Dict,
                      zones: Dict[str, Tuple[float, float, float, float]],
                      use_relative: bool = True,
                      font: str = FONT_NAME,
                      font_size: int = FONT_SIZE) -> None:
    """
    payload 구조:
      {
        "texts": {
          "T": { "사고일시": (rx,ry,val) or (x,y,val), ... },
          "A": {...}, "B": {...}, "C": {...}, "D": {...}, "E": {...}
        },
        "checks": {
          "D": [ (rx,ry,on,size,style) or (x,y,on,size,style), ... ],
          ...
        },
        "circles": {
          "D": [ (rx,ry,r,on,mode) or (cx,cy,r,on,mode), ... ],
          ...
        }
      }
    zones: { "T": (x,y,w,h), "A": (...), ... }  # 페이지 절대좌표
    """
    doc = fitz.open(src_page3_pdf)
    page = doc[0]
    page.insert_font(fontname=font, fontfile=FONT_PATH)

    # 텍스트
    for zone_name, items in payload.get("texts", {}).items():
        if zone_name not in zones:
            raise ValueError(f"zones 정의에 '{zone_name}' 없음")
        for label, coords in items.items():
            if use_relative:
                rx, ry, val = coords
                x, y = _rel_to_abs(zones[zone_name], rx, ry)
            else:
                x, y, val = coords
            insert_text(page, x, y, str(val), font=font, size=font_size)

    # 체크박스
    for zone_name, arr in payload.get("checks", {}).items():
        if zone_name not in zones:
            raise ValueError(f"zones 정의에 '{zone_name}' 없음")
        for item in arr:
            if use_relative:
                rx, ry, on, size, style = item
                x, y = _rel_to_abs(zones[zone_name], rx, ry)
            else:
                x, y, on, size, style = item
            draw_checkbox(page, x, y, on, box=size, font=font, style=style)

    # 동그라미/라디오
    for zone_name, arr in payload.get("circles", {}).items():
        if zone_name not in zones:
            raise ValueError(f"zones 정의에 '{zone_name}' 없음")
        for item in arr:
            if use_relative:
                rx, ry, r, on, mode = item
                cx, cy = _rel_to_abs(zones[zone_name], rx, ry)
            else:
                cx, cy, r, on, mode = item
            draw_circle_mark(page, cx, cy, r, checked=on, mode=mode)

    doc.save(out_pdf, deflate=True)
    doc.close()


# ------------------------
# 예시 실행 (필요 경로/좌표는 실제 값으로 보정)
# ------------------------
if __name__ == "__main__":
    # 0) 원본 PDF에서 3페이지만 추출
    src_full = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\4.교통사고 신속처리 협의서\1.원본\교통사고+신속처리+표준+협의서(한글버전)_upload_인쇄.pdf"
    page3_pdf = "p3_only.pdf"
    extract_page3(src_full, page3_pdf)

    # 1) 좌표 보정용 그리드 (처음 한 번 만들어 눈금 보고 zones 치수 확정)
    # draw_grid_for_calibration(page3_pdf, "p3_grid.pdf", step=50)

    # 2) 구역 박스 정의 (x,y,w,h) — p3_grid.pdf를 보고 실제 값으로 수정
    #    아래 값들은 예시입니다. 반드시 페이지 픽셀 기준 실측값으로 바꾸세요.
    zones = {
        "T": (60, 80, 680, 80),     # 상단 T영역
        "A": (60, 170, 340, 250),   # 왼쪽 A영역
        "B": (410, 170, 330, 250),  # 가운데 B영역
        "C": (750, 170, 120, 250),  # 오른쪽 C영역
        "D": (60, 430, 810, 100),   # 사고형태/원인 등
        "E": (60, 540, 810, 120),   # 사고내용 자유기술
    }

    # 3) 페이로드 (구역상대 좌표: rx, ry는 0~1)
    payload = {
        "texts": {
            "T": {
                "사고일시": (0.10, 0.30, "2025-08-10 14:32"),
                "사고장소": (0.10, 0.65, "서울 서초구 반포대로 201 교차로"),
                "날씨":     (0.85, 0.25, "맑음"),
            },
            "A": {
                "성명":     (0.15, 0.12, "홍길동"),
                "연락처":   (0.15, 0.24, "010-1234-5678"),
                "주민번호": (0.15, 0.36, "950101-0002000"),
                "주소":     (0.15, 0.48, "서울 서초구 반포대로 201"),
                "차량번호": (0.15, 0.60, "12가 3456"),
                "보험사":   (0.15, 0.72, "현대해상"),
                "탑승인원": (0.70, 0.72, "남1, 여1"),
            },
            "B": {
                "성명":     (0.15, 0.12, "김철수"),
                "연락처":   (0.15, 0.24, "010-9876-5432"),
                "주민번호": (0.15, 0.36, "930202-1234567"),
                "주소":     (0.15, 0.48, "서울 강남구 ..."),
                "차량번호": (0.15, 0.60, "78나 9012"),
                "보험사":   (0.15, 0.72, "삼성화재"),
                "탑승인원": (0.70, 0.72, "남0, 여1"),
            },
            "C": {
                "성명":     (0.10, 0.12, "피해자 성명"),
                "주민번호": (0.10, 0.28, "000101-3******"),
                "전화":     (0.10, 0.44, "010-0000-0000"),
                "주소":     (0.10, 0.60, "서울시 ..."),
                "특이사항": (0.10, 0.80, "파손 부위 기재"),
            },
            "E": {
                "사고내용": (0.05, 0.18, "교차로 직진 중 접촉. 인명피해 없음. 현장 사진 촬영 완료."),
            },
        },
        "checks": {
            # 예: D구역 체크박스들 (rx, ry, on, size, style)
            "D": [
                (0.10, 0.15, True,  12, "check"),  # '대인 없음'
                (0.20, 0.15, False, 12, "check"),  # '대인 있음'
            ],
        },
        "circles": {
            # 예: D구역 사고형태 라디오 버튼 3개
            "D": [
                (0.35, 0.55, 6, True,  "radio"),   # 자동차 대 자동차
                (0.55, 0.55, 6, False, "radio"),   # 자동차 대 보행자
                (0.75, 0.55, 6, False, "radio"),   # 기타
            ],
        },
    }

    # 4) 렌더 & 저장
    out_pdf = "accident_p3_filled.pdf"
    fill_page3_grouped(
        src_page3_pdf=page3_pdf,
        out_pdf=out_pdf,
        payload=payload,
        zones=zones,
        use_relative=True,           # 구역상대 좌표 사용
        font=FONT_NAME,
        font_size=FONT_SIZE,
    )

    print("생성 완료:", Path(out_pdf).resolve())
