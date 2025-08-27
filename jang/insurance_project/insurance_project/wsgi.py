# insurance_project/wsgi.py
import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

# 프로젝트 루트
BASE_DIR = Path(__file__).resolve().parent.parent

# 별도 보관된 앱 루트 추가(insurance_portal이 여기 존재)
EXTRA_APP_ROOT = BASE_DIR / "0826-5"
sp = str(EXTRA_APP_ROOT)
if sp not in sys.path:
    sys.path.insert(0, sp)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "insurance_project.settings")
application = get_wsgi_application()
