# -*- coding: utf-8 -*-
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json, logging


logger = logging.getLogger(__name__)

@csrf_exempt
def fault_answer_view(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        body = json.loads(request.body.decode("utf-8"))
        query = (body.get("query") or "").strip()
        if not query:
            return JsonResponse({"ok": False, "error": "empty query"}, status=400)

        from insurance_portal.services.fault_answerer import answer_fault
        result = answer_fault(query)
        return JsonResponse({"ok": True, "result": result}, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        logger.exception("fault_answer_view error: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
