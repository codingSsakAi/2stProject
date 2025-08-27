from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import datetime
from io import BytesIO
from .constants import PART_ANCHORS, LABEL_COLORS
from .models import Agreement  # <-- 추가
import json, re

# PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# ---- 공통 헬퍼: DB에서 레코드 읽고 payload 복원 ----
def _get_agreement_payload_or_404(pk: int):
    rec = get_object_or_404(Agreement, pk=pk)
    try:
        payload = json.loads(rec.damages_raw or "{}")
    except json.JSONDecodeError:
        payload = {}
    return rec, payload



# ---------------------------
# 1) 폼 화면 (GET 전용)
# ---------------------------
@require_http_methods(["GET"])
def form_view(request):
    return render(
        request,
        "accident_project/form.html",
        {"part_anchors": PART_ANCHORS, "label_colors": LABEL_COLORS},
    )


# ---------------------------
# 유틸들
# ---------------------------
def mask_rrn_value(v: str) -> str:
    if not v:
        return v
    m = re.match(r'^(\d{6})-(\d)(\d{6})$', v)
    return f'{m.group(1)}-{m.group(2)}******' if m else v

def _collect_markers(prefix: str, POST) -> list:
    markers = []
    for i in range(1, 6):
        x = POST.get(f'{prefix}_x_{i}')
        y = POST.get(f'{prefix}_y_{i}')
        if x and y:
            try:
                markers.append({"x": float(x), "y": float(y)})
            except ValueError:
                pass
    return markers

def _collect_payload(request: HttpRequest) -> dict:
    P = request.POST
    F = {
        # 메타
        "accident_date": P.get("accident_date"),
        "location": P.get("location"),

        # A 차량
        "a_plate": P.get("a_plate"),
        "a_insurer": P.get("a_insurer"),
        "a_name": P.get("a_name"),
        "a_id": P.get("a_id"),
        "a_phone": P.get("a_phone"),
        "a_address": P.get("a_address"),
        "a_damage_desc": P.get("a_damage_desc"),

        # B 차량
        "b_plate": P.get("b_plate"),
        "b_insurer": P.get("b_insurer"),
        "b_name": P.get("b_name"),
        "b_id": P.get("b_id"),
        "b_phone": P.get("b_phone"),
        "b_address": P.get("b_address"),
        "b_damage_desc": P.get("b_damage_desc"),

        # 보행자
        "p_name": P.get("p_name"),
        "p_id": P.get("p_id"),
        "p_phone": P.get("p_phone"),
        "p_address": P.get("p_address"),
        "p_damage_desc": P.get("p_damage_desc"),

        # 사건 개요
        "accident_description": P.get("accident_description"),

        # 다중 선택(배열)
        "weather": P.getlist("weather"),
        "type_cc": P.getlist("type_cc"),
        "type_cp": P.getlist("type_cp"),
        "cause": P.getlist("cause"),
    }
    # 파손 마커
    F["a_markers"] = _collect_markers("a", P)
    F["b_markers"] = _collect_markers("b", P)
    return F


# ---------------------------
# 2) 저장(POST) -> pk 리다이렉트
# ---------------------------
@require_http_methods(["POST"])
def agreement_submit(request: HttpRequest) -> HttpResponse:
    F = _collect_payload(request)

    out_format = request.POST.get("format", "pdf")
    mask_rrn = request.POST.get("mask_rrn") in ("true", "on", "1")

    # Agreement 모델에 저장
    rec = Agreement.objects.create(
        incident_dt=(F.get("accident_date") or "")[:32],
        location=F.get("location") or "",
        a_name=F.get("a_name") or "",
        b_name=F.get("b_name") or "",
        damages_raw=json.dumps(F, ensure_ascii=False),
    )
    pk = rec.pk

    url = reverse("accident_project:agreement_print", kwargs={"pk": pk})
    url += f"?mask_rrn={'true' if mask_rrn else 'false'}&format={out_format}"
    return redirect(url)


# ---------------------------
# 3) 최종 출력(서버 템플릿 렌더)
# ---------------------------
@require_http_methods(["GET"])
def agreement_print(request: HttpRequest, pk: int) -> HttpResponse:
    rec = get_object_or_404(Agreement, pk=pk)
    try:
        F = json.loads(rec.damages_raw or "{}")
    except json.JSONDecodeError:
        F = {}

    # 주민번호 마스킹 옵션
    mask_rrn = request.GET.get("mask_rrn") in ("true", "on", "1")
    if mask_rrn:
        F = dict(F)  # 얕은 복사
        F["a_id_masked"] = mask_rrn_value(F.get("a_id"))
        F["b_id_masked"] = mask_rrn_value(F.get("b_id"))
        F["p_id_masked"] = mask_rrn_value(F.get("p_id"))

    ctx = {
        "F": F,
        "pk": pk,
        "mask_rrn": mask_rrn,
        "suggested_basename": f"pk_{pk}__{(F.get('accident_date') or '')[:10]}_{F.get('a_plate') or 'UNKNOWN'}",
    }
    return render(request, "accident_project/print.html", ctx)


# ---------------------------
# 4) (선택) PDF/JPG 다운로드도 pk 기반으로
# ---------------------------

def download_pdf(request, pk=None):
    # pk는 agreement_print와 동일하게 받아서 데이터 조회
    rec = _get_demo_record_or_404(request, pk)   # 세션/DB에서 가져오기
    data = rec["form_payload"]

    # PDF 만들기
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, f"사고일시: {data.get('accident_date','')}")
    p.drawString(100, 780, f"A차량: {data.get('a_name','')}")
    p.drawString(100, 760, f"B차량: {data.get('b_name','')}")
    p.save()

    buffer.seek(0)
    filename = f"agreement_{pk}.pdf"
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

# def download_pdf(request: HttpRequest, pk: int) -> HttpResponse:
#     rec = get_object_or_404(Agreement, pk=pk)
#     try:
#         data = json.loads(rec.damages_raw or "{}")
#     except json.JSONDecodeError:
#         data = {}

#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#     width, height = A4

#     # 한글 폰트 등록(환경에 맞게 경로 조정)
#     try:
#         pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
#         p.setFont("Malgun", 16)
#     except Exception:
#         p.setFont("Helvetica-Bold", 16)

#     p.drawString(160, height - 50, "Traffic Accident Agreement")
#     p.setFont("Helvetica", 12)
#     y = height - 100
#     fields = [
#         ("Accident Date", data.get("accident_date", "")),
#         ("Location", data.get("location", "")),
#         ("Weather", ", ".join(data.get("weather", []))),
#         ("A Vehicle Plate", data.get("a_plate", "")),
#         ("A Vehicle Insurer", data.get("a_insurer", "")),
#         ("A Driver Name", data.get("a_name", "")),
#         ("A Driver Phone", data.get("a_phone", "")),
#         ("B Vehicle Plate", data.get("b_plate", "")),
#         ("B Vehicle Insurer", data.get("b_insurer", "")),
#         ("B Driver Name", data.get("b_name", "")),
#         ("B Driver Phone", data.get("b_phone", "")),
#         ("Accident Description", data.get("accident_description", "")),
#     ]
#     for label, value in fields:
#         if y < 50:
#             p.showPage()
#             y = height - 50
#             p.setFont("Helvetica", 12)
#         p.drawString(50, y, f"{label}: {value}")
#         y -= 22

#     p.save()
#     buffer.seek(0)

#     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"pk_{pk}__{(data.get('accident_date') or '')[:10]}_{data.get('a_plate') or 'UNKNOWN'}.pdf"
#     resp = HttpResponse(buffer.getvalue(), content_type="application/pdf")
#     resp["Content-Disposition"] = f'attachment; filename="{filename}"'
#     return resp


# @require_http_methods(["GET"])
# def download_image(request: HttpRequest, pk: int) -> HttpResponse:
#     rec = get_object_or_404(Agreement, pk=pk)
#     try:
#         data = json.loads(rec.damages_raw or "{}")
#     except json.JSONDecodeError:
#         data = {}

#     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"pk_{pk}__{(data.get('accident_date') or '')[:10]}_{data.get('a_plate') or 'UNKNOWN'}.txt"
#     content = f"""교통사고 협의서

# 사고일시: {data.get('accident_date', '')}
# 사고장소: {data.get('location', '')}
# 날씨: {", ".join(data.get("weather", []))}

# A차량:
# - 차량번호: {data.get('a_plate', '')}
# - 보험회사: {data.get('a_insurer', '')}
# - 운전자: {data.get('a_name', '')}
# - 전화번호: {data.get('a_phone', '')}

# B차량:
# - 차량번호: {data.get('b_plate', '')}
# - 보험회사: {data.get('b_insurer', '')}
# - 운전자: {data.get('b_name', '')}
# - 전화번호: {data.get('b_phone', '')}

# 사고내용: {data.get('accident_description', '')}
# """
#     resp = HttpResponse(content, content_type="text/plain; charset=utf-8")
#     resp["Content-Disposition"] = f'attachment; filename="{filename}"'
#     return resp

def download_image(request, pk=None):
    rec = _get_demo_record_or_404(request, pk)
    data = rec["form_payload"]

    content = f"""
    사고일시: {data.get('accident_date','')}
    A차량: {data.get('a_name','')}
    B차량: {data.get('b_name','')}
    """
    filename = f"agreement_{pk}.txt"   # 실제 JPG로 만들려면 PIL 필요
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

@require_http_methods(["GET"])
def agreement_preview(request):
    F = {
        # 메타
        "accident_date": "", "location": "", "weather": [],
        # A
        "a_plate": "", "a_insurer": "", "a_name": "", "a_id": "", "a_phone": "",
        "a_address": "", "a_male": "0", "a_female": "0", "a_damage_desc": "",
        "a_parts": [], "a_markers": [],
        # B
        "b_plate": "", "b_insurer": "", "b_name": "", "b_id": "", "b_phone": "",
        "b_address": "", "b_male": "0", "b_female": "0", "b_damage_desc": "",
        "b_parts": [], "b_markers": [],
        # 보행자
        "p_name": "", "p_id": "", "p_phone": "", "p_address": "", "p_damage_desc": "",
        # 사고형태/원인
        "type_cc": [], "type_cp": [], "cause": [], "accident_description": "",
    }
    return render(request, "accident_project/print.html",
                  {"F": F, "pk": None, "mask_rrn": False})