# insurance_portal/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.template.loader import render_to_string

EXCLUDE_URL_NAMES = {"login", "signup"}

class PortalInjectorMiddleware(MiddlewareMixin):
    """
    로그인/회원가입을 제외한 모든 HTML 응답의 </body> 직전에
    insurance_portal 번들 파셜을 주입한다.
    """
    def process_response(self, request, response):
        try:
            ctype = response.get("Content-Type", "")
            if (
                response.status_code == 200
                and "text/html" in ctype
                and not getattr(response, "streaming", False)
                and hasattr(request, "resolver_match")
            ):
                url_name = getattr(request.resolver_match, "url_name", None)
                if url_name in EXCLUDE_URL_NAMES:
                    return response

                body = response.content.decode(response.charset, errors="ignore")
                idx = body.lower().rfind("</body>")
                if idx == -1:
                    return response

                snippet = render_to_string(
                    "insurance_portal/partials/_portal_inject.html",
                    request=request,
                    context={},
                )
                new_body = body[:idx] + snippet + body[idx:]
                response.content = new_body.encode(response.charset)
                if response.has_header("Content-Length"):
                    response["Content-Length"] = str(len(response.content))
        except Exception:
            return response
        return response
