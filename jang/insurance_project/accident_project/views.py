# accident_project/views.py
from datetime import datetime
import json, re
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.clickjacking import xframe_options_sameorigin  # ★ 추가

from .constants import LABEL_COLORS, PART_ANCHORS
from .models import AccidentRecord, Agreement

# PDF fallback
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# ---------------------------
# 상수 옵션 (템플릿과 일치)
# ---------------------------
INSURER_OPTIONS = [
    "삼성화재","현대해상","DB손해보험","KB손해보험","메리츠화재",
    "한화손보","흥국화재","롯데손보","농협손보","MG손보","AXA","캐롯"
]

WEATHER_OPTIONS = ["맑음", "흐림", "비", "눈", "안개"]
CC_OPTIONS = ["정면충돌", "후미추돌(진행중)", "후미추돌(주정차중)", "측면충돌", "후진사고"]
CP_OPTIONS = ["횡단보도 통행중", "무단횡단중", "차도가장자리 통행중", "보도 통행중"]
CAUSE_OPTIONS = ["음주운전", "신호위반", "중앙선 침범", "과속", "횡단보도위반", "기타"]


# ---------------------------
# 공통 유틸
# ---------------------------

def index(request):
    """
    /accident/ 진입점.
    index 템플릿이 있으면 렌더, 없으면 협의서 작성으로 리다이렉트.
    """
    try:
        return render(request, "accident_project/index.html")
    except Exception:
        return redirect("accident_project:agreement_form")


def _get_agreement_payload_or_404(pk: int):
    rec = get_object_or_404(Agreement, pk=pk)
    try:
        payload = json.loads(rec.damages_raw or "{}")
    except json.JSONDecodeError:
        payload = {}
    return rec, payload


def mask_rrn_value(v: str) -> str:
    if not v:
        return v
    m = re.match(r"^(\d{6})-(\d)(\d{6})$", v)
    return f"{m.group(1)}-{m.group(2)}******" if m else v


def _fmt_k(dtstr: str) -> str:
    """YYYY-MM-DD HH:mm 로 표시용 포맷."""
    if not dtstr:
        return ""
    s = dtstr.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return s


def _as_int(x):
    try:
        return int(x)
    except Exception:
        return 0


def _parse_local_dt_to_aware(s: str):
    """
    'YYYY-MM-DDTHH:MM' 또는 그 변형 문자열을 timezone-aware datetime으로 변환.
    실패 시 None 반환.
    """
    if not s:
        return None
    s = str(s).strip()
    # 1) ISO-like
    dt = parse_datetime(s)
    if dt:
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    # 2) 'YYYY-MM-DDTHH:MM' 또는 'YYYY-MM-DD HH:MM'
    s = s.replace("T", " ")
    try:
        dt = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        return timezone.make_aware(dt)
    except Exception:
        return None


# ---------------------------
# 홈
# ---------------------------
def home(request):
    return render(request, "home.html")


# ---------------------------
# 신규 작성 폼
# ---------------------------
def _new_form_context():
    return {
        "F": {
            "accident_date": "",
            "location": "",
            "weather": [],
            "type_cc": [],
            "type_cp": [],
            "cause": [],
            "a_male": "0",
            "a_female": "0",
            "b_male": "0",
            "b_female": "0",
            "a_parts_json": "[]",
            "b_parts_json": "[]",
            "a_markers_json": "[]",
            "b_markers_json": "[]",
            "accident_description": "",
        },
        "part_anchors": PART_ANCHORS,
        "label_colors": LABEL_COLORS,
        "weather_options": WEATHER_OPTIONS,
        "cc_options": CC_OPTIONS,
        "cp_options": CP_OPTIONS,
        "cause_options": CAUSE_OPTIONS,
        "insurer_options": INSURER_OPTIONS,
        "edit_mode": False,
        "form_action": reverse("accident_project:agreement_submit"),
    }

@login_required
@require_http_methods(["GET"])
def agreement_form(request):
    """신규 작성 화면 (기존 /agreements/new/)."""
    return render(request, "accident_project/form.html", _new_form_context())


# ---------------------------
# 저장(POST) → 출력으로 리다이렉트
# ---------------------------
@login_required
@require_http_methods(["POST"])
def agreement_submit(request: HttpRequest):
    P = request.POST
    F = {
        # 메타
        "accident_date": P.get("accident_date") or "",
        "location": P.get("location") or "",
        # A
        "a_plate": P.get("a_plate") or "",
        "a_insurer": P.get("a_insurer") or "",
        "a_name": P.get("a_name") or "",
        "a_id": P.get("a_id") or "",
        "a_phone": P.get("a_phone") or "",
        "a_address": P.get("a_address") or "",
        "a_male": P.get("a_male") or "0",
        "a_female": P.get("a_female") or "0",
        "a_damage_desc": P.get("a_damage_desc") or "",
        # B
        "b_plate": P.get("b_plate") or "",
        "b_insurer": P.get("b_insurer") or "",
        "b_name": P.get("b_name") or "",
        "b_id": P.get("b_id") or "",
        "b_phone": P.get("b_phone") or "",
        "b_address": P.get("b_address") or "",
        "b_male": P.get("b_male") or "0",
        "b_female": P.get("b_female") or "0",
        "b_damage_desc": P.get("b_damage_desc") or "",
        # 보행자
        "p_name": P.get("p_name") or "",
        "p_id": P.get("p_id") or "",
        "p_phone": P.get("p_phone") or "",
        "p_address": P.get("p_address") or "",
        "p_damage_desc": P.get("p_damage_desc") or "",
        # 다중 선택/배열
        "weather": P.getlist("weather"),
        "type_cc": P.getlist("type_cc"),
        "type_cp": P.getlist("type_cp"),
        "cause": P.getlist("cause"),
        # 선택부위/마킹(JSON 문자열)
        "a_parts_json": P.get("a_parts_json") or "[]",
        "b_parts_json": P.get("b_parts_json") or "[]",
        "a_markers_json": P.get("a_markers_json") or "[]",
        "b_markers_json": P.get("b_markers_json") or "[]",
        # 서술
        "accident_description": P.get("accident_description") or "",
    }

    ag = Agreement.objects.create(
        owner=request.user,
        incident_dt=_parse_local_dt_to_aware(F["accident_date"]),
        location=F["location"],
        a_name=F["a_name"],
        b_name=F["b_name"],
        damages_raw=json.dumps(F, ensure_ascii=False),
    )

    out_format = P.get("format", "pdf")
    mask_rrn = P.get("mask_rrn") in ("true", "on", "1")

    url = reverse("accident_project:agreement_print", kwargs={"pk": ag.pk})
    url += f"?mask_rrn={'true' if mask_rrn else 'false'}&format={out_format}"
    return redirect(url)


# ---------------------------
# 최종 출력 (팝업에서도 열림)
# ---------------------------
@login_required
@xframe_options_sameorigin  # ★ 안전하게 same-origin 임베드 허용
def agreement_print(request: HttpRequest, pk: int):
    rec, F = _get_agreement_payload_or_404(pk)
    if rec.owner_id != request.user.id:
        return HttpResponseForbidden("본인 문서만 조회할 수 있습니다.")

    F = dict(F)

    # 배열/마킹 복원
    def _safe_arr(key):
        v = F.get(key, "[]")
        if isinstance(v, list):
            return v
        try:
            return json.loads(v or "[]")
        except Exception:
            return []
    F["a_parts"] = _safe_arr("a_parts_json")
    F["b_parts"] = _safe_arr("b_parts_json")
    F["a_markers"] = _safe_arr("a_markers_json")
    F["b_markers"] = _safe_arr("b_markers_json")

    # 마스킹 옵션
    mask = request.GET.get("mask_rrn") in ("true", "on", "1")
    if mask:
        F["a_id_masked"] = mask_rrn_value(F.get("a_id"))
        F["b_id_masked"] = mask_rrn_value(F.get("b_id"))
        F["p_id_masked"] = mask_rrn_value(F.get("p_id"))

    # 표시용
    F["accident_date_display"] = _fmt_k(F.get("accident_date"))
    F["a_total"] = str(_as_int(F.get("a_male")) + _as_int(F.get("a_female")))
    F["b_total"] = str(_as_int(F.get("b_male")) + _as_int(F.get("b_female")))

    return render(
        request,
        "accident_project/print.html",
        {
            "F": F,
            "pk": rec.pk,
            "mask_rrn": mask,
            "part_anchors": PART_ANCHORS,
            "label_colors": LABEL_COLORS,
            "in_preview": request.GET.get("in_preview") in ("1","true"),  # 팝업일 때 일부 버튼 숨김
        },
    )


# ---------------------------
# 서버 PDF/JPG Fallback
# ---------------------------
@login_required
@xframe_options_sameorigin
def agreement_pdf(request, pk):
    rec, data = _get_agreement_payload_or_404(pk)
    if rec.owner_id != request.user.id:
        return HttpResponseForbidden("본인 문서만 다운로드할 수 있습니다.")

    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(180, y, "Traffic Accident Agreement")
    y -= 30
    p.setFont("Helvetica", 11)
    lines = [
        ("사고일시", data.get("accident_date", "")),
        ("사고장소", data.get("location", "")),
        ("A차량 운전자", data.get("a_name", "")),
        ("B차량 운전자", data.get("b_name", "")),
        ("A차량 번호", data.get("a_plate", "")),
        ("B차량 번호", data.get("b_plate", "")),
        ("사고 개요", data.get("accident_description", "")),
    ]
    for k, v in lines:
        p.drawString(60, y, f"{k}: {v}")
        y -= 18
        if y < 40:
            p.showPage()
            y = h - 40
            p.setFont("Helvetica", 11)
    p.save()
    buf.seek(0)

    filename = f"agreement_{pk}.pdf"
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
@xframe_options_sameorigin
def agreement_image(request, pk):
    rec, data = _get_agreement_payload_or_404(pk)
    if rec.owner_id != request.user.id:
        return HttpResponseForbidden("본인 문서만 다운로드할 수 있습니다.")

    content = f"""교통사고 협의서(요약)
사고일시: {data.get('accident_date','')}
사고장소: {data.get('location','')}
A 운전자: {data.get('a_name','')}  / 차량: {data.get('a_plate','')}
B 운전자: {data.get('b_name','')}  / 차량: {data.get('b_plate','')}
사고 개요: {data.get('accident_description','')}
"""
    filename = f"agreement_{pk}.txt"
    resp = HttpResponse(content, content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ---------------------------
# 미리보기(로컬스토리지 기반)
# ---------------------------
@login_required
@require_http_methods(["GET"])
@xframe_options_sameorigin
def agreement_preview(request: HttpRequest):
    F = {
        "accident_date": "", "location": "", "weather": [],
        # A
        "a_plate": "", "a_insurer": "", "a_name": "", "a_id": "", "a_phone": "", "a_address": "",
        "a_male": "0", "a_female": "0", "a_damage_desc": "",
        "a_parts_json": "[]", "a_markers_json": "[]",
        # B
        "b_plate": "", "b_insurer": "", "b_name": "", "b_id": "", "b_phone": "", "b_address": "",
        "b_male": "0", "b_female": "0", "b_damage_desc": "",
        "b_parts_json": "[]", "b_markers_json": "[]",
        # 보행자
        "p_name": "", "p_id": "", "p_phone": "", "p_address": "", "p_damage_desc": "",
        # 분류
        "type_cc": [], "type_cp": [], "cause": [],
        # 서술
        "accident_description": "",
    }
    return render(
        request,
        "accident_project/print.html",
        {
            "F": F,
            "pk": None,
            "mask_rrn": False,
            "in_preview": True,   # 미리보기 모드 → 다운로드/저장 버튼 감춤
            "part_anchors": PART_ANCHORS,
            "label_colors": LABEL_COLORS,
        },
    )


# ---------------------------
# 마이페이지(레거시 AccidentRecord)
# ---------------------------
@login_required
def mypage(request):
    qs = AccidentRecord.objects.filter(owner=request.user).order_by("-accident_date", "-id")
    page = Paginator(qs, 3).get_page(request.GET.get("page"))
    ctx = {"agreements": page, "user": request.user}
    return render(request, "accident_project/mypage.html", ctx)


@login_required
def record_detail(request, pk: int):
    rec = get_object_or_404(AccidentRecord, pk=pk, owner=request.user)
    F = rec.payload or {}
    if request.method == "POST":
        try:
            payload = json.loads(request.POST.get("payload_json") or "{}")
        except Exception:
            payload = {}
        rec.accident_date = payload.get("accident_date") or rec.accident_date
        rec.location = payload.get("location", rec.location)
        rec.a_plate = payload.get("a_plate", rec.a_plate)
        rec.b_plate = payload.get("b_plate", rec.b_plate)
        rec.payload = payload
        rec.save()
    ctx = {"rec": rec, "F": F}
    return render(request, "accident_project/form.html", ctx)


@login_required
def record_print(request, pk: int):
    rec = get_object_or_404(AccidentRecord, pk=pk, owner=request.user)
    F = rec.payload or {}
    ctx = {"F": F, "pk": rec.pk}
    return render(request, "accident_project/print.html", ctx)


@login_required
@require_POST
def record_upsert_api(request):
    body = request.body.decode("utf-8") or "{}"
    try:
        data = json.loads(body)
    except Exception:
        data = {}

    accident_date = data.get("accident_date")  # ISO
    adt = parse_datetime(accident_date) or timezone.now()

    obj, created = AccidentRecord.objects.update_or_create(
        owner=request.user,
        accident_date=adt,
        a_plate=data.get("a_plate", ""),
        b_plate=data.get("b_plate", ""),
        defaults=dict(location=data.get("location", ""), payload=data.get("payload") or {}),
    )
    return JsonResponse({"ok": True, "id": obj.pk, "created": created})


# ---------------------------
# Agreement 리스트(마이페이지)
# ---------------------------
def _title_date_from_agreement(ag) -> str | None:
    s = getattr(ag, "incident_dt", None)
    if not s:
        try:
            s = (json.loads(ag.damages_raw or "{}") or {}).get("accident_date")
        except Exception:
            s = None
    if not s:
        return None

    if hasattr(s, "strftime"):
        dt = s
    else:
        s = str(s).replace("T", " ")
        dt = parse_datetime(s)
        if not dt:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s[:16], fmt)
                    break
                except Exception:
                    pass

    return dt.strftime("%Y.%m.%d") if dt else str(s)[:10].replace("-", ".")

@login_required
def mypage_agreements(request):
    qs = Agreement.objects.filter(owner=request.user).order_by("-created_at")
    page_obj = Paginator(qs, 9).get_page(request.GET.get("page") or 1)

    for ag in page_obj:
        d = _title_date_from_agreement(ag)
        ag.title_text = f"{d} 교통사고 협의서" if d else "날짜미상 교통사고 협의서"

    return render(request, "accident_project/mypage_agreements.html", {"agreements": page_obj})


# ---------------------------
# Agreement 수정/삭제/미리보기(저장본)
# ---------------------------
@login_required
def agreement_edit(request, pk):
    ag = get_object_or_404(Agreement, pk=pk)

    if getattr(ag, "owner_id", None) is None:
        ag.owner = request.user
        ag.save(update_fields=["owner"])
    if ag.owner_id != request.user.id:
        return HttpResponseForbidden("본인 소유 문서만 수정할 수 있습니다.")

    try:
        F = json.loads(ag.damages_raw or "{}")
    except Exception:
        F = {}

    def _arr(key):
        v = F.get(key)
        if isinstance(v, list):
            return v
        try:
            return json.loads(v or "[]")
        except Exception:
            return []

    F["a_parts"] = _arr("a_parts_json")
    F["b_parts"] = _arr("b_parts_json")
    F["a_markers"] = _arr("a_markers_json")
    F["b_markers"] = _arr("b_markers_json")

    ctx = {
        "F": F,
        "part_anchors": PART_ANCHORS,
        "label_colors": LABEL_COLORS,
        "weather_options": WEATHER_OPTIONS,
        "cc_options": CC_OPTIONS,
        "cp_options": CP_OPTIONS,
        "cause_options": CAUSE_OPTIONS,
        "insurer_options": INSURER_OPTIONS,
        "edit_mode": True,
        "form_action": reverse("accident_project:agreement_update", kwargs={"pk": ag.pk}),
    }
    return render(request, "accident_project/form.html", ctx)


@login_required
@require_POST
def agreement_delete(request, pk):
    ag = get_object_or_404(Agreement, pk=pk)

    if getattr(ag, "owner_id", None) is None:
        ag.owner = request.user
        ag.save(update_fields=["owner"])

    if ag.owner_id != request.user.id:
        return HttpResponseForbidden("본인 문서만 삭제할 수 있습니다.")

    ag.delete()
    messages.success(request, "협의서가 삭제되었습니다. 복구는 불가능합니다.")
    return redirect("accident_project:mypage_agreements")


@login_required
@require_POST
def agreement_update(request, pk):
    ag = get_object_or_404(Agreement, pk=pk)

    if getattr(ag, "owner_id", None) is None:
        ag.owner = request.user
        ag.save(update_fields=["owner"])
    if ag.owner_id != request.user.id:
        return HttpResponseForbidden("본인 소유 문서만 수정할 수 있습니다.")

    P = request.POST
    F = {
        "accident_date": P.get("accident_date") or "",
        "location": P.get("location") or "",
        "a_plate": P.get("a_plate") or "",
        "a_insurer": P.get("a_insurer") or "",
        "a_name": P.get("a_name") or "",
        "a_id": P.get("a_id") or "",
        "a_phone": P.get("a_phone") or "",
        "a_address": P.get("a_address") or "",
        "a_male": P.get("a_male") or "0",
        "a_female": P.get("a_female") or "0",
        "a_damage_desc": P.get("a_damage_desc") or "",
        "b_plate": P.get("b_plate") or "",
        "b_insurer": P.get("b_insurer") or "",
        "b_name": P.get("b_name") or "",
        "b_id": P.get("b_id") or "",
        "b_phone": P.get("b_phone") or "",
        "b_address": P.get("b_address") or "",
        "b_male": P.get("b_male") or "0",
        "b_female": P.get("b_female") or "0",
        "b_damage_desc": P.get("b_damage_desc") or "",
        "p_name": P.get("p_name") or "",
        "p_id": P.get("p_id") or "",
        "p_phone": P.get("p_phone") or "",
        "p_address": P.get("p_address") or "",
        "p_damage_desc": P.get("p_damage_desc") or "",
        "weather": P.getlist("weather"),
        "type_cc": P.getlist("type_cc"),
        "type_cp": P.getlist("type_cp"),
        "cause": P.getlist("cause"),
        "a_parts_json": P.get("a_parts_json") or "[]",
        "b_parts_json": P.get("b_parts_json") or "[]",
        "a_markers_json": P.get("a_markers_json") or "[]",
        "b_markers_json": P.get("b_markers_json") or "[]",
        "accident_description": P.get("accident_description") or "",
    }

    ag.incident_dt = _parse_local_dt_to_aware(F["accident_date"])
    ag.location = F["location"]
    ag.a_name = F["a_name"]
    ag.b_name = F["b_name"]
    ag.damages_raw = json.dumps(F, ensure_ascii=False)
    ag.save(update_fields=["incident_dt", "location", "a_name", "b_name", "damages_raw"])

    messages.success(request, "협의서가 수정되었습니다.")
    return redirect("accident_project:mypage_agreements")


@login_required
@xframe_options_sameorigin
def agreement_preview_saved(request, pk):
    rec = get_object_or_404(Agreement, pk=pk)
    if getattr(rec, "owner_id", None) is None:
        rec.owner = request.user
        rec.save(update_fields=["owner"])
    if rec.owner_id != request.user.id:
        return HttpResponseForbidden("본인 문서만 미리보기 할 수 있습니다.")

    try:
        F = json.loads(rec.damages_raw or "{}")
    except Exception:
        F = {}

    def _arr(key):
        v = F.get(key)
        if isinstance(v, list):
            return v
        try:
            return json.loads(v or "[]")
        except Exception:
            return []

    F["a_parts"] = _arr("a_parts_json")
    F["b_parts"] = _arr("b_parts_json")
    F["a_markers"] = _arr("a_markers_json")
    F["b_markers"] = _arr("b_markers_json")

    mask = request.GET.get("mask_rrn") in ("true", "on", "1")
    if mask:
        F["a_id_masked"] = mask_rrn_value(F.get("a_id"))
        F["b_id_masked"] = mask_rrn_value(F.get("b_id"))
        F["p_id_masked"] = mask_rrn_value(F.get("p_id"))

    F["accident_date_display"] = _fmt_k(F.get("accident_date"))
    F["a_total"] = str(_as_int(F.get("a_male")) + _as_int(F.get("a_female")))
    F["b_total"] = str(_as_int(F.get("b_male")) + _as_int(F.get("b_female")))

    return render(
        request,
        "accident_project/print.html",
        {
            "F": F,
            "pk": rec.pk,
            "mask_rrn": mask,
            "in_preview": True,   # 팝업/미리보기 모드
            "part_anchors": PART_ANCHORS,
            "label_colors": LABEL_COLORS,
        },
    )
