import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4

# ✅ 양식 이미지에 텍스트를 매핑할 좌표 (template.png 기준)
FIELD_COORDINATES = {
    'accident_date': (120, 60),
    'location': (120, 90),

    'a_name': (100, 135),
    'a_phone': (100, 165),
    'a_id': (100, 195),
    'a_address': (100, 225),
    'a_passengers': (100, 255),
    'a_damage': (100, 295),

    'b_name': (470, 135),
    'b_phone': (470, 165),
    'b_id': (470, 195),
    'b_address': (470, 225),
    'b_passengers': (470, 255),
    'b_damage': (470, 295),

    'description': (100, 415),
    'weather': (100, 455)
}

def generate_image(data, output_path, template_path):
    """
    template.png 위에 사용자 입력 데이터를 주어진 좌표에 렌더링하여 JPG 이미지 생성
    """
    # ✅ 이미지 열기
    image = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    # ✅ 한글 폰트 설정 (Windows 환경 기준)
    font_path = "C:/Windows/Fonts/malgun.ttf"
    font = ImageFont.truetype(font_path, 18)

    # ✅ 각 필드별 위치에 텍스트 출력
    for key, value in data.items():
        coord = FIELD_COORDINATES.get(key)
        if coord:
            draw.text(coord, str(value), fill="black", font=font)

    # ✅ 이미지 저장
    image.save(output_path)


def generate_pdf(image_path, pdf_path):
    """
    A4 가로형 PDF로 이미지 삽입 후 저장
    """
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))  # A4 가로
    c.drawImage(image_path, 0, 0, width=842, height=595)  # 사이즈에 맞게 출력
    c.showPage()
    c.save()
