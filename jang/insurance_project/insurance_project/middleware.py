# insurance_project/middleware.py
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


# ─────────────────────────────────────────────────────────────
#  A) /static/insurance_portal/**  →  0826-5/insurance_portal/static/** 브릿지
#     (정적 경로 등록이 안 되어 있어도 원본 파일을 서빙)
# ─────────────────────────────────────────────────────────────
class PortalStaticBridgeMiddleware(MiddlewareMixin):
    """
    /static/insurance_portal/** 요청을 0826-5 폴더(또는 후보 경로)에서 직접 읽어 반환.
    다른 정적 파일은 건드리지 않음.
    """
    URL_PREFIX = "/static/insurance_portal/"

    def __init__(self, get_response):
        super().__init__(get_response)
        # 후보 루트(우선순위: 0826-5 → 프로젝트 루트 → fallback)
        base: Path = settings.BASE_DIR
        self.candidate_roots: list[Path] = [
            base / "0826-5" / "insurance_portal" / "static" / "insurance_portal",
            base / "insurance_portal" / "static" / "insurance_portal",
            base / "insurance_app" / "static" / "insurance_portal",  # 혹시 기존에 원본이 여기 있을 수도 있음
        ]

    def _try_open(self, relpath: str) -> tuple[bytes | None, str | None]:
        for root in self.candidate_roots:
            f = root / relpath
            if f.exists() and f.is_file():
                data = f.read_bytes()
                ctype, _ = mimetypes.guess_type(str(f))
                return data, ctype or "application/octet-stream"
        return None, None

    def __call__(self, request):
        path = request.path
        if path.startswith(self.URL_PREFIX):
            rel = path[len(self.URL_PREFIX):]  # 'js/...' 또는 'css/...' 등
            data, ctype = self._try_open(rel)
            if data is not None:
                resp = HttpResponse(data, content_type=ctype)
                # 간단 캐시 헤더(개발용)
                resp["Cache-Control"] = "max-age=300, public"
                return resp
        return self.get_response(request)


# ─────────────────────────────────────────────────────────────
#  B) HTML 응답에 원본 토글(CSS/JS) 자동 주입
#     - 템플릿을 수정하지 않아도 됨
# ─────────────────────────────────────────────────────────────
class PortalAutoInjectMiddleware(MiddlewareMixin):
    """
    text/html 응답 본문에 원본 토글 CSS/JS를 자동 삽입.
    - admin/static/media 경로 등은 제외
    - 이미 삽입돼 있으면 재삽입하지 않음
    """
    EXCLUDE_PREFIXES: tuple[str, ...] = ("/admin", "/static", "/media")
    MARKER = b"<!-- __PORTAL_INJECTED__ -->"

    def __init__(self, get_response):
        super().__init__(get_response)
        # 존재 확인용 파일 후보 (있을 때만 링크 주입)
        self.css_candidates: list[str] = [
            "/static/insurance_portal/css/portal.css",
            "/static/insurance_portal/portal.css",
            "/static/insurance_portal/style.css",
            "/static/insurance_portal/styles.css",
        ]
        self.js_candidates: list[str] = [
            "/static/insurance_portal/loader_strict.js",  # 우리가 쓰던 로더 (있으면 베스트)
            "/static/insurance_portal/loader.js",
            "/static/insurance_portal/portal.js",
            "/static/insurance_portal/js/portal.js",      # 아카이브에서 확인된 경로
        ]

    def _exists(self, url_path: str) -> bool:
        # 우리의 StaticBridge가 /static/insurance_portal/**를 처리하므로,
        # 파일 존재 체크는 로컬 디스크 기준으로도 함께 수행
        prefix = "/static/insurance_portal/"
        if not url_path.startswith(prefix):
            return False
        rel = url_path[len(prefix):]
        for root in [
            settings.BASE_DIR / "0826-5" / "insurance_portal" / "static" / "insurance_portal",
            settings.BASE_DIR / "insurance_portal" / "static" / "insurance_portal",
            settings.BASE_DIR / "insurance_app" / "static" / "insurance_portal",
        ]:
            f = root / rel
            if f.exists():
                return True
        return False

    def _pick_first(self, urls: Iterable[str]) -> str | None:
        for u in urls:
            if self._exists(u):
                return u
        return None

    def __call__(self, request):
        # 제외 경로
        for p in self.EXCLUDE_PREFIXES:
            if request.path.startswith(p):
                return self.get_response(request)

        resp = self.get_response(request)

        # HTML 200 OK 만 대상으로
        ctype = resp.headers.get("Content-Type", "")
        if resp.status_code != 200 or "text/html" not in ctype:
            return resp
        if not hasattr(resp, "content"):
            return resp
        # 이미 삽입됐다면 스킵
        if self.MARKER in resp.content:
            return resp

        # 주입할 리소스 결정(실존하는 것만)
        css_url = self._pick_first(self.css_candidates)
        js_url  = self._pick_first(self.js_candidates)

        if not css_url and not js_url:
            return resp  # 넣을 게 없으면 스킵

        # body 닫히기 직전에 삽입
        try:
            charset = resp.charset or "utf-8"
        except Exception:
            charset = "utf-8"

        html = resp.content.decode(charset, errors="ignore")
        inject_parts = ['\n', '<!-- __PORTAL_INJECTED__ -->', '\n']
        if css_url:
            inject_parts.append(f'<link rel="stylesheet" href="{css_url}?v=1" />\n')
        if js_url:
            inject_parts.append(f'<script src="{js_url}?v=1" defer></script>\n')

        payload = "".join(inject_parts)
        if "</body>" in html:
            html = html.replace("</body>", payload + "</body>")
        else:
            html = html + payload

        resp.content = html.encode(charset)
        # 길이 갱신
        if resp.has_header("Content-Length"):
            resp.headers["Content-Length"] = str(len(resp.content))
        return resp
