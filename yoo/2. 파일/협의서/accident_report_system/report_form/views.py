# report_form/views.py
from django.shortcuts import render
from django.http import FileResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from playwright.sync_api import sync_playwright
from io import BytesIO

@csrf_exempt
def generate_report(request):
    if request.method != "POST":
        return render(request, "report_form/form.html")

    fmt = request.POST.get("format", "pdf")  # 'pdf' or 'jpg'

    # --- 1) 체크박스 등 다중값 필드는 join, 그 외는 단일값으로 평탄화 ---
    multi_keys = {"weather", "type_cc", "type_cp", "cause"}  # 다중 선택 필드 이름
    flat = {}
    for k in request.POST.keys():
        if k in multi_keys:
            # 같은 이름이 여러 개 있으니 getlist로 받아서 문자열로
            vals = [v for v in request.POST.getlist(k) if v]
            flat[k] = vals
        else:
            # 단일값만 유지(리스트 방지)
            flat[k] = request.POST.get(k, "")

    # 숫자 합계(탑승인원)
    def to_int(v):
        try: return int(v)
        except: return 0
    a_male = to_int(flat.get("a_male", 0)); a_female = to_int(flat.get("a_female", 0))
    b_male = to_int(flat.get("b_male", 0)); b_female = to_int(flat.get("b_female", 0))

    # --- 2) 템플릿 컨텍스트 구성 (print.html에서 바로 사용) ---
    context = {
        **flat,
        "type_cc_join": " , ".join(flat.get("type_cc", [])) if flat.get("type_cc") else "-",
        "type_cp_join": " , ".join(flat.get("type_cp", [])) if flat.get("type_cp") else "-",
        "cause_join":   " , ".join(flat.get("cause", []))   if flat.get("cause")   else "-",
        "weather_join": " , ".join(flat.get("weather", [])) if flat.get("weather") else "-",
        "a_total": a_male + a_female,
        "b_total": b_male + b_female,
        "base_url": request.build_absolute_uri("/"),
        # 마킹 좌표 추가
        "a_x_1": flat.get("a_x_1", ""), "a_y_1": flat.get("a_y_1", ""),
        "a_x_2": flat.get("a_x_2", ""), "a_y_2": flat.get("a_y_2", ""),
        "a_x_3": flat.get("a_x_3", ""), "a_y_3": flat.get("a_y_3", ""),
        "a_x_4": flat.get("a_x_4", ""), "a_y_4": flat.get("a_y_4", ""),
        "a_x_5": flat.get("a_x_5", ""), "a_y_5": flat.get("a_y_5", ""),
        "b_x_1": flat.get("b_x_1", ""), "b_y_1": flat.get("b_y_1", ""),
        "b_x_2": flat.get("b_x_2", ""), "b_y_2": flat.get("b_y_2", ""),
        "b_x_3": flat.get("b_x_3", ""), "b_y_3": flat.get("b_y_3", ""),
        "b_x_4": flat.get("b_x_4", ""), "b_y_4": flat.get("b_y_4", ""),
        "b_x_5": flat.get("b_x_5", ""), "b_y_5": flat.get("b_y_5", ""),
    }

    html = render_to_string("report_form/print.html", context)

    # --- 3) Playwright로 A4(landscape) PDF/JPG 생성 ---
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 화면에서 A4를 정확히 스크린샷하려면 viewport를 충분히 크게 + 2배 스케일
        context_pw = browser.new_context(device_scale_factor=2)
        page = context_pw.new_page()
        page.set_content(html, wait_until="networkidle")
        page.emulate_media(media="print")  # @page 규칙 반영

        if fmt == "jpg":
            # #sheet 요소만 정확히 캡처(=A4 landscape)
            box = page.locator("#sheet").bounding_box()
            img_bytes = page.screenshot(
                type="jpeg",
                quality=92,
                clip=box
            )
            browser.close()
            return FileResponse(BytesIO(img_bytes), as_attachment=True, filename="accident_report.jpg")

        # PDF는 A4 landscape로 바로 출력
        pdf_bytes = page.pdf(
            format="A4",
            landscape=True,
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
        )
        browser.close()
        return FileResponse(BytesIO(pdf_bytes), as_attachment=True, filename="accident_report.pdf")
