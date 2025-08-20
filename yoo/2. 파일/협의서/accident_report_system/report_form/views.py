from django.shortcuts import render
from django.http import FileResponse
from django.conf import settings
from .forms import AccidentForm
from .utils import generate_image, generate_pdf
import os

def generate_report(request):
    if request.method == 'POST':
        form = AccidentForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # ✅ 폴더 먼저 생성해줌
            report_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
            os.makedirs(report_dir, exist_ok=True)  # ★ 이 줄이 중요

            # 경로 설정
            img_path = os.path.join(report_dir, 'result.jpg')
            pdf_path = os.path.join(report_dir, 'result.pdf')
            template_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'template.png')

            # 파일 생성
            generate_image(data, img_path, template_path)
            generate_pdf(img_path, pdf_path)

            return FileResponse(open(pdf_path, 'rb'), as_attachment=True)
    else:
        form = AccidentForm()
    return render(request, 'report_form/form.html', {'form': form})