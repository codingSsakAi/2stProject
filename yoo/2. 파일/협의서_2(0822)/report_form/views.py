# report_form/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from datetime import datetime
import json

# PDF 생성용 - 일단 간단한 방법 사용
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO

@require_http_methods(["GET", "POST"])
def form_view(request):
    if request.method == "POST":
        g = request.POST.get
        getlist = request.POST.getlist

        # format 파라미터 확인
        format_type = g("format", "")
        print(f"Format type: {format_type}")

        data = {
            # 상단 메타
            "accident_date": g("accident_date", ""),
            "location": g("location", ""),
            "weather": getlist("weather"),
        }
        data["weather_join"] = ", ".join(data["weather"]) if data["weather"] else ""

        # A 차량
        data.update({
            "a_plate": g("a_plate", ""),
            "a_insurer": g("a_insurer", ""),
            "a_name": g("a_name", ""),
            "a_id": g("a_id", ""),
            "a_phone": g("a_phone", ""),
            "a_address": g("a_address", ""),
            "a_male": g("a_male", "0"),
            "a_female": g("a_female", "0"),
            "a_damage_desc": g("a_damage_desc", ""),
        })
        
        # B 차량
        data.update({
            "b_plate": g("b_plate", ""),
            "b_insurer": g("b_insurer", ""),
            "b_name": g("b_name", ""),
            "b_id": g("b_id", ""),
            "b_phone": g("b_phone", ""),
            "b_address": g("b_address", ""),
            "b_male": g("b_male", "0"),
            "b_female": g("b_female", "0"),
            "b_damage_desc": g("b_damage_desc", ""),
        })

        # 보행자 정보
        data.update({
            "p_name": g("p_name", ""),
            "p_id": g("p_id", ""),
            "p_phone": g("p_phone", ""),
            "p_address": g("p_address", ""),
            "p_damage_desc": g("p_damage_desc", ""),
        })

        # 사고 내용
        data.update({
            "type_cc": getlist("type_cc"),
            "type_cp": getlist("type_cp"),
            "cause": getlist("cause"),
            "accident_description": g("accident_description", ""),
        })
        
        # 조인된 문자열 생성
        data["type_cc_join"] = ", ".join(data["type_cc"]) if data["type_cc"] else ""
        data["type_cp_join"] = ", ".join(data["type_cp"]) if data["type_cp"] else ""
        data["cause_join"] = ", ".join(data["cause"]) if data["cause"] else ""

        # 파손 마킹 데이터
        data.update({
            "a_marks": g("a_marks", "[]"),
            "b_marks": g("b_marks", "[]"),
            "a_x_1": g("a_x_1", ""),
            "a_y_1": g("a_y_1", ""),
            "a_x_2": g("a_x_2", ""),
            "a_y_2": g("a_y_2", ""),
            "b_x_1": g("b_x_1", ""),
            "b_y_1": g("b_y_1", ""),
            "b_x_2": g("b_x_2", ""),
            "b_y_2": g("b_y_2", ""),
        })

        # 인원수 계산
        try:
            a_total = int(data["a_male"] or 0) + int(data["a_female"] or 0)
        except ValueError:
            a_total = 0
        data["a_total"] = a_total

        try:
            b_total = int(data["b_male"] or 0) + int(data["b_female"] or 0)
        except ValueError:
            b_total = 0
        data["b_total"] = b_total

        # 세션 저장
        print(f"Saving data to session: {len(str(data))} characters")
        request.session["agreement_data"] = data
        request.session.modified = True
        
        # 세션 저장 확인
        saved_data = request.session.get("agreement_data")
        print(f"Session save check: {saved_data is not None}")

        # namespace를 사용한 redirect
        if format_type == "pdf":
            return redirect("report_form:download_pdf")
        elif format_type == "jpg":
            return redirect("report_form:download_image")
        else:
            return redirect("report_form:agreement_print")

    return render(request, "report_form/form.html")

def download_pdf(request):
    """PDF 다운로드 - ReportLab 사용"""
    print("download_pdf view called")
    
    # 세션 확인
    print(f"Session keys: {list(request.session.keys())}")
    
    data = request.session.get("agreement_data")
    print(f"Retrieved data: {data is not None}")
    
    if not data:
        print("No data found in session, redirecting...")
        return redirect("report_form:agreement_form")
    
    try:
        # PDF 생성
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # 제목
        p.setFont("Helvetica-Bold", 16)
        p.drawString(200, height - 50, "Traffic Accident Agreement")
        
        # 내용 (한글 지원을 위해 기본 폰트 사용)
        p.setFont("Helvetica", 12)
        y_position = height - 100
        
        # 데이터 출력
        fields = [
            ("Accident Date", data.get('accident_date', '')),
            ("Location", data.get('location', '')),
            ("Weather", data.get('weather_join', '')),
            ("A Vehicle Plate", data.get('a_plate', '')),
            ("A Vehicle Insurer", data.get('a_insurer', '')),
            ("A Driver Name", data.get('a_name', '')),
            ("A Driver Phone", data.get('a_phone', '')),
            ("B Vehicle Plate", data.get('b_plate', '')),
            ("B Vehicle Insurer", data.get('b_insurer', '')),
            ("B Driver Name", data.get('b_name', '')),
            ("B Driver Phone", data.get('b_phone', '')),
            ("Accident Description", data.get('accident_description', '')),
        ]
        
        for label, value in fields:
            if y_position < 50:  # 페이지 끝에 도달하면 새 페이지
                p.showPage()
                y_position = height - 50
                p.setFont("Helvetica", 12)
            
            p.drawString(50, y_position, f"{label}: {value}")
            y_position -= 25
        
        p.save()
        buffer.seek(0)
        
        # 파일 이름 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"traffic_accident_agreement_{timestamp}.pdf"
        
        # HTTP 응답 생성
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"PDF 생성 오류: {e}")
        return HttpResponse(f"PDF 생성 오류: {str(e)}", content_type='text/plain; charset=utf-8')

def download_image(request):
    """이미지 다운로드 - 간단한 텍스트 파일로 대체"""
    print("download_image view called")
    
    data = request.session.get("agreement_data")
    if not data:
        return redirect("report_form:agreement_form")
    
    try:
        # 텍스트 내용 생성
        content = f"""교통사고 협의서
        
사고일시: {data.get('accident_date', '')}
사고장소: {data.get('location', '')}
날씨: {data.get('weather_join', '')}

A차량 정보:
- 차량번호: {data.get('a_plate', '')}
- 보험회사: {data.get('a_insurer', '')}
- 운전자: {data.get('a_name', '')}
- 전화번호: {data.get('a_phone', '')}

B차량 정보:
- 차량번호: {data.get('b_plate', '')}
- 보험회사: {data.get('b_insurer', '')}
- 운전자: {data.get('b_name', '')}
- 전화번호: {data.get('b_phone', '')}

사고내용: {data.get('accident_description', '')}
"""
        
        # 파일 이름 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"교통사고협의서_{timestamp}.txt"
        
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        print(f"파일 생성 오류: {e}")
        return HttpResponse(f"파일 생성 오류: {str(e)}", content_type='text/plain; charset=utf-8')

def print_view(request):
    """브라우저 인쇄용 페이지"""
    print("print_view called")
    
    data = request.session.get("agreement_data")
    if not data:
        print("No data for print view")
        return redirect("report_form:agreement_form")
    
    print(f"Print view data keys: {list(data.keys())}")
    return render(request, "report_form/print.html", data)

def agreement_print(request):
    """기존 함수와 호환성 유지"""
    return print_view(request)