from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.urls import reverse
from django.utils import timezone
import re

from django.views.decorators.http import require_http_methods
from datetime import datetime
from io import BytesIO
from .constants import PART_ANCHORS, LABEL_COLORS
import json

# PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

@require_http_methods(["GET", "POST"])
def form_view(request):
    if request.method == "POST":
        g = request.POST.get
        getlist = request.POST.getlist

        format_type = g("format", "")
        data = {
            "accident_date": g("accident_date", ""),
            "location": g("location", ""),
            "weather": getlist("weather"),
        }
        data["weather_join"] = ", ".join(data["weather"]) if data["weather"] else ""

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

        data.update({
            "p_name": g("p_name", ""),
            "p_id": g("p_id", ""),
            "p_phone": g("p_phone", ""),
            "p_address": g("p_address", ""),
            "p_damage_desc": g("p_damage_desc", ""),
        })

        data.update({
            "type_cc": getlist("type_cc"),
            "type_cp": getlist("type_cp"),
            "cause": getlist("cause"),
            "accident_description": g("accident_description", ""),
        })
        data["type_cc_join"] = ", ".join(data["type_cc"]) if data["type_cc"] else ""
        data["type_cp_join"] = ", ".join(data["type_cp"]) if data["type_cp"] else ""
        data["cause_join"] = ", ".join(data["cause"]) if data["cause"] else ""

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

        # ✅ A/B 손상부위(체크박스 선택 순서) 수집 — JS가 hidden에 넣어줌
        try:
            data["a_parts"] = json.loads(g("a_parts_json", "[]"))
        except json.JSONDecodeError:
            data["a_parts"] = []
        try:
            data["b_parts"] = json.loads(g("b_parts_json", "[]"))
        except json.JSONDecodeError:
            data["b_parts"] = []

        # 인원 합계/세션 저장/리다이렉트는 네 코드 그대로
        # ...

        fmt = request.POST.get("format", "")
        if fmt == "pdf":
            return redirect("accident_project:download_pdf")
        elif fmt == "jpg":
            return redirect("accident_project:download_image")
        return redirect("accident_project:agreement_print")

    # ✅ GET: 네임스페이스 경로 + JS 상수 내려주기
    ctx = {"part_anchors": PART_ANCHORS, "label_colors": LABEL_COLORS}
    
    return render(request, "accident_project/form.html", {
        "part_anchors": PART_ANCHORS,
        "label_colors": LABEL_COLORS,
    })

def download_pdf(request):
    data = request.session.get("agreement_data")
    if not data:
        return redirect("accident_project:agreement_form")

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 한글 필요 시 폰트 등록(윈도우 예시)
    pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
    p.setFont("Malgun", 16)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Traffic Accident Agreement")

    p.setFont("Helvetica", 12)
    y = height - 100
    fields = [
        ("Accident Date", data.get("accident_date", "")),
        ("Location", data.get("location", "")),
        ("Weather", data.get("weather_join", "")),
        ("A Vehicle Plate", data.get("a_plate", "")),
        ("A Vehicle Insurer", data.get("a_insurer", "")),
        ("A Driver Name", data.get("a_name", "")),
        ("A Driver Phone", data.get("a_phone", "")),
        ("B Vehicle Plate", data.get("b_plate", "")),
        ("B Vehicle Insurer", data.get("b_insurer", "")),
        ("B Driver Name", data.get("b_name", "")),
        ("B Driver Phone", data.get("b_phone", "")),
        ("Accident Description", data.get("accident_description", "")),
    ]
    for label, value in fields:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)
        p.drawString(50, y, f"{label}: {value}")
        y -= 25

    p.save()
    buffer.seek(0)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"traffic_accident_agreement_{ts}.pdf"
    resp = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def download_image(request):
    data = request.session.get("agreement_data")
    if not data:
        return redirect("accident_project:agreement_form")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"agreement_{ts}.txt"
    content = f"""교통사고 협의서

사고일시: {data.get('accident_date', '')}
사고장소: {data.get('location', '')}
날씨: {data.get('weather_join', '')}

A차량:
- 차량번호: {data.get('a_plate', '')}
- 보험회사: {data.get('a_insurer', '')}
- 운전자: {data.get('a_name', '')}
- 전화번호: {data.get('a_phone', '')}

B차량:
- 차량번호: {data.get('b_plate', '')}
- 보험회사: {data.get('b_insurer', '')}
- 운전자: {data.get('b_name', '')}
- 전화번호: {data.get('b_phone', '')}

사고내용: {data.get('accident_description', '')}
"""
    resp = HttpResponse(content, content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

def print_view(request):
    data = request.session.get("agreement_data")
    if not data:
        return redirect("accident_project:agreement_form")

    ctx = {
        **data,
        "a_parts": data.get("a_parts", []),
        "b_parts": data.get("b_parts", []),
        "part_anchors": PART_ANCHORS,
        "label_colors": LABEL_COLORS,
    }
    return render(request, "accident_project/print.html", ctx)

def agreement_print(request):
    return print_view(request)


# 가정: models.py에 JSONField가 있는 레코드가 존재
# from .models import AccidentRecord

# 임시 모델 대체 설명:
# AccidentRecord(form_payload=dict, a_plate=str, created_at=datetime)
# 실제 프로젝트에 맞춰 models.py에 정의 후 import 하세요.

def mask_rrn_value(v: str) -> str:
    if not v:
        return v
    m = re.match(r'^(\d{6})-(\d)(\d{6})$', v)
    return f'{m.group(1)}-{m.group(2)}******' if m else v

def _collect_markers(prefix: str, POST) -> list:
    # a_x_1..5, a_y_1..5 → [{x,y},...]
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

    # 파손 마커(% 좌표 최대 5개)
    F["a_markers"] = _collect_markers("a", P)
    F["b_markers"] = _collect_markers("b", P)

    return F

def agreement_submit(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        # 폼으로 돌려보내거나 405
        return redirect("/")

    F = _collect_payload(request)

    # 파일명에 사용할 기준
    a_plate = F.get("a_plate") or "UNKNOWN"
    accident_date = (F.get("accident_date") or "")[:10]  # YYYY-MM-DD

    # format/mask 옵션
    out_format = request.POST.get("format", "pdf")
    mask_rrn = request.POST.get("mask_rrn") in ("true", "on", "1")

    # DB 저장 (실제 프로젝트 모델 사용)
    # rec = AccidentRecord.objects.create(
    #     form_payload=F,
    #     a_plate=a_plate,
    #     accident_date=accident_date or timezone.now().date(),
    # )

    # 여기서는 데모를 위해 세션에 저장(pk 대체) — 실제로는 위 모델을 사용하세요.
    rec_list = request.session.get("demo_records", [])
    pk = (rec_list[-1]["pk"] + 1) if rec_list else 1
    rec = {"pk": pk, "form_payload": F, "a_plate": a_plate, "accident_date": accident_date}
    rec_list.append(rec)
    request.session["demo_records"] = rec_list

    # 최종 출력 페이지로 이동
    url = reverse("accident_project:agreement_print", kwargs={"pk": pk})
    url += f"?mask_rrn={'true' if mask_rrn else 'false'}&format={out_format}"
    return redirect(url)

def _get_demo_record_or_404(request, pk: int) -> dict:
    rec_list = request.session.get("demo_records", [])
    for r in rec_list:
        if r["pk"] == pk:
            return r
    from django.http import Http404
    raise Http404("record not found")

def agreement_print(request: HttpRequest, pk: int) -> HttpResponse:
    # 실제: rec = get_object_or_404(AccidentRecord, pk=pk)
    rec = _get_demo_record_or_404(request, pk)
    F = rec["form_payload"]

    # 주민번호 마스킹 옵션
    mask_rrn = request.GET.get("mask_rrn") in ("true", "on", "1")
    if mask_rrn:
        F = dict(F)  # 얕은 복사 후 마스킹 필드 추가
        F["a_id_masked"] = mask_rrn_value(F.get("a_id"))
        F["b_id_masked"] = mask_rrn_value(F.get("b_id"))
        F["p_id_masked"] = mask_rrn_value(F.get("p_id"))

    ctx = {
        "F": F,
        "pk": pk,
        "mask_rrn": mask_rrn,
        # 파일명 규칙: pk__date__plate.ext — 실제 다운로드 시 헤더에 적용 가능
        "suggested_basename": f"pk_{pk}__{rec.get('accident_date') or timezone.now().date()}_{rec.get('a_plate') or 'UNKNOWN'}",
    }
    return render(request, "print.html", ctx)

def agreement_preview(request: HttpRequest) -> HttpResponse:
    # 같은 템플릿을 미리보기 모드로 사용(로컬스토리지 주입)
    return render(request, "print.html", {"F": {}, "pk": None, "mask_rrn": False})