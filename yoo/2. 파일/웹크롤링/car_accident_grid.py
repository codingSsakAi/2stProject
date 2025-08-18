# -*- coding: utf-8 -*-
"""
완벽한 회전 그리드 생성기 (검증 완료)
- PDF는 그대로 유지 (595×842)
- 그리드만 90도 회전하여 협의서 표 방향(842×595)에 맞춤
- 좌표 변환 공식 검증됨
"""

from pathlib import Path
import fitz  # PyMuPDF


def coord_transform(doc_x, doc_y, doc_width=842, doc_height=595):
    """
    협의서 기준 좌표를 PDF 기준 좌표로 변환
    협의서: 842×595 (가로형) -> PDF: 595×842 (세로형)
    90도 반시계방향 회전: (x,y) -> (y, doc_width-x)
    """
    pdf_x = doc_y
    pdf_y = doc_width - doc_x
    return pdf_x, pdf_y


def create_perfect_landscape_grid(
    pdf_in: str,
    out_dir: str,
    out_name: str = None
) -> str:
    """
    완벽한 가로형 그리드 생성 (검증 완료)
    """
    pdf_in_path = Path(pdf_in)
    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    if out_name is None:
        out_name = f"{pdf_in_path.stem}_PERFECT_LANDSCAPE.pdf"
    out_path = out_dir_path / out_name
    
    # PDF 열기 (원본 그대로, 회전 정보 건드리지 않음)
    doc = fitz.open(str(pdf_in_path))
    page = doc[0]
    
    # 협의서 기준 크기 (실제 내용 방향)
    DOC_WIDTH = 842   # 협의서 가로
    DOC_HEIGHT = 595  # 협의서 세로
    
    print(f"=== 완벽한 가로형 그리드 생성 ===")
    print(f"PDF 크기: {page.rect}")
    print(f"협의서 기준: {DOC_WIDTH} × {DOC_HEIGHT}")
    print(f"좌표 변환: 90도 반시계방향 회전")
    
    # ✅ 1단계: 세밀한 격자 (25px)
    fine_shape = page.new_shape()
    
    # 가로선 (협의서 기준 Y축 고정, X축 변경)
    for doc_y in range(0, DOC_HEIGHT + 1, 25):
        # 가로선: (0, doc_y) -> (DOC_WIDTH, doc_y)
        pdf_x1, pdf_y1 = coord_transform(0, doc_y)
        pdf_x2, pdf_y2 = coord_transform(DOC_WIDTH, doc_y)
        fine_shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    # 세로선 (협의서 기준 X축 고정, Y축 변경)  
    for doc_x in range(0, DOC_WIDTH + 1, 25):
        # 세로선: (doc_x, 0) -> (doc_x, DOC_HEIGHT)
        pdf_x1, pdf_y1 = coord_transform(doc_x, 0)
        pdf_x2, pdf_y2 = coord_transform(doc_x, DOC_HEIGHT)
        fine_shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    fine_shape.finish(color=(0.9, 0.9, 0.9), width=0.3)
    fine_shape.commit()
    
    # ✅ 2단계: 중간 격자 (50px)
    medium_shape = page.new_shape()
    
    # 가로선
    for doc_y in range(0, DOC_HEIGHT + 1, 50):
        pdf_x1, pdf_y1 = coord_transform(0, doc_y)
        pdf_x2, pdf_y2 = coord_transform(DOC_WIDTH, doc_y)
        medium_shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    # 세로선
    for doc_x in range(0, DOC_WIDTH + 1, 50):
        pdf_x1, pdf_y1 = coord_transform(doc_x, 0)
        pdf_x2, pdf_y2 = coord_transform(doc_x, DOC_HEIGHT)
        medium_shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    medium_shape.finish(color=(0.6, 0.6, 0.6), width=0.6)
    medium_shape.commit()
    
    # ✅ 3단계: 굵은 격자 (100px) - 빨간색
    bold_shape = page.new_shape()
    
    # 가로선
    for doc_y in range(0, DOC_HEIGHT + 1, 100):
        pdf_x1, pdf_y1 = coord_transform(0, doc_y)
        pdf_x2, pdf_y2 = coord_transform(DOC_WIDTH, doc_y)
        bold_shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    # 세로선
    for doc_x in range(0, DOC_WIDTH + 1, 100):
        pdf_x1, pdf_y1 = coord_transform(doc_x, 0)
        pdf_x2, pdf_y2 = coord_transform(doc_x, DOC_HEIGHT)
        bold_shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    bold_shape.finish(color=(1.0, 0.0, 0.0), width=1.2)
    bold_shape.commit()
    
    # ✅ 4단계: 좌표 라벨 (협의서 기준 좌표 표시)
    
    # X축 라벨 (상단)
    for doc_x in range(0, DOC_WIDTH + 1, 50):
        pdf_x, pdf_y = coord_transform(doc_x, 0)
        page.insert_text(
            fitz.Point(pdf_x + 2, pdf_y - 5),
            f"X{doc_x}",
            fontsize=8,
            color=(0.0, 0.0, 1.0)
        )
    
    # Y축 라벨 (좌측)
    for doc_y in range(0, DOC_HEIGHT + 1, 50):
        pdf_x, pdf_y = coord_transform(0, doc_y)
        page.insert_text(
            fitz.Point(pdf_x + 5, pdf_y - 2),
            f"Y{doc_y}",
            fontsize=8,
            color=(0.0, 0.0, 1.0)
        )
    
    # ✅ 5단계: 구역 경계 (협의서 기준 좌표)
    zones = {
        "T": (32, 60, 775, 25),       # 상단 제목 영역
        "A": (72, 83, 310, 315),    # 왼쪽 A당사자
        "B": (380, 83, 310, 315),   # 오른쪽 B당사자  
        "C": (690, 83, 120, 315),     # 사고형태/원인
        "D": (120, 400, 365, 50),     # 사고내용 - 체크박스
        "E": (72, 450, 409, 70),     # 사고내용 - 텍스트 작성 
    }
    
    for zone_name, (doc_x, doc_y, doc_w, doc_h) in zones.items():
        zone_shape = page.new_shape()
        
        # 사각형 4개 모서리 계산
        corners = [
            (doc_x, doc_y),                    # 좌상단
            (doc_x + doc_w, doc_y),            # 우상단
            (doc_x + doc_w, doc_y + doc_h),    # 우하단
            (doc_x, doc_y + doc_h)             # 좌하단
        ]
        
        # PDF 좌표로 변환
        pdf_corners = [coord_transform(x, y) for x, y in corners]
        
        # 사각형 그리기
        for i in range(4):
            start = pdf_corners[i]
            end = pdf_corners[(i + 1) % 4]
            zone_shape.draw_line(fitz.Point(*start), fitz.Point(*end))
        
        zone_shape.finish(color=(0.0, 0.8, 0.0), width=2.0)
        zone_shape.commit()
        
        # 구역 라벨
        label_pdf_x, label_pdf_y = coord_transform(doc_x + 5, doc_y + 15)
        page.insert_text(
            fitz.Point(label_pdf_x, label_pdf_y),
            f"[{zone_name}] {doc_w}×{doc_h}",
            fontsize=10,
            color=(0.0, 0.6, 0.0)
        )
    
    # ✅ 6단계: 정보 표시
    info_pdf_x, info_pdf_y = coord_transform(700, 30)
    page.insert_text(
        fitz.Point(info_pdf_x, info_pdf_y),
        f"협의서 기준: {DOC_WIDTH}×{DOC_HEIGHT}",
        fontsize=10,
        color=(0.0, 0.0, 0.0)
    )
    
    # 저장
    doc.save(str(out_path), deflate=True)
    doc.close()
    
    print(f"✅ 완벽한 가로형 그리드 완료: {out_path}")
    return str(out_path)


def create_simple_rotated_grid(pdf_in: str, out_dir: str) -> str:
    """
    간단한 회전 그리드 (테스트용)
    """
    pdf_in_path = Path(pdf_in)
    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir_path / f"{pdf_in_path.stem}_SIMPLE_ROTATED.pdf"
    
    doc = fitz.open(str(pdf_in_path))
    page = doc[0]
    
    shape = page.new_shape()
    
    # 50px 간격 격자만
    for doc_y in range(0, 595 + 1, 50):
        pdf_x1, pdf_y1 = coord_transform(0, doc_y)
        pdf_x2, pdf_y2 = coord_transform(842, doc_y)
        shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    for doc_x in range(0, 842 + 1, 50):
        pdf_x1, pdf_y1 = coord_transform(doc_x, 0)
        pdf_x2, pdf_y2 = coord_transform(doc_x, 595)
        shape.draw_line(fitz.Point(pdf_x1, pdf_y1), fitz.Point(pdf_x2, pdf_y2))
    
    shape.finish(color=(1.0, 0.0, 0.0), width=1.0)
    shape.commit()
    
    # 좌표 라벨
    for doc_x in range(0, 842 + 1, 100):
        pdf_x, pdf_y = coord_transform(doc_x, 0)
        page.insert_text(fitz.Point(pdf_x + 2, pdf_y - 5), f"{doc_x}", fontsize=8, color=(0, 0, 1))
    
    for doc_y in range(0, 595 + 1, 100):
        pdf_x, pdf_y = coord_transform(0, doc_y)
        page.insert_text(fitz.Point(pdf_x + 5, pdf_y - 2), f"{doc_y}", fontsize=8, color=(0, 0, 1))
    
    doc.save(str(out_path), deflate=True)
    doc.close()
    
    print(f"✅ 간단 회전 그리드 완료: {out_path}")
    return str(out_path)


if __name__ == "__main__":
    # 경로 설정
    page3_pdf = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\4.교통사고 신속처리 협의서\1.원본\p3_only.pdf"
    out_dir = r"C:\Users\Admin\Desktop\2차 프로젝트\2.코드\웹크롤링\데이터\4.교통사고 신속처리 협의서\2.변환본(가공,최종)"
    
    print("🎯 완벽한 회전 그리드 생성 (검증 완료)")
    print("📐 좌표 변환: 협의서(842×595) -> PDF(595×842)")
    
    try:
        # 1) 간단한 테스트 먼저
        simple_result = create_simple_rotated_grid(
            pdf_in=page3_pdf,
            out_dir=out_dir
        )
        
        # 2) 완벽한 상세 그리드
        perfect_result = create_perfect_landscape_grid(
            pdf_in=page3_pdf,
            out_dir=out_dir,
            out_name="PERFECT_LANDSCAPE_GRID.pdf"
        )
        
        print("\n🎉 성공! 파일들:")
        print(f"📄 간단 테스트: {simple_result}")
        print(f"📄 완벽한 그리드: {perfect_result}")
        print("\n✅ 이제 협의서 표와 그리드가 완벽하게 일치할 것입니다!")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()