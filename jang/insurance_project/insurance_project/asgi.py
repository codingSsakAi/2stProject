# insurance_project/asgi.py
import os
import sys
from pathlib import Path
from django.core.asgi import get_asgi_application

BASE_DIR = Path(__file__).resolve().parent.parent

# 별도 보관된 앱 루트 추가
EXTRA_APP_ROOT = BASE_DIR / "0826-5"
sp = str(EXTRA_APP_ROOT)
if sp not in sys.path:
    sys.path.insert(0, sp)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "insurance_project.settings")
application = get_asgi_application()
