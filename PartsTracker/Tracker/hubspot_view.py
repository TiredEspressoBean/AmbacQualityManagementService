import json
import hmac
import hashlib

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import Orders

def verify_signature(request):
    """Optional: Verify the X-HubSpot-Signature header"""
    secret = getattr(settings, "HUBSPOT_WEBHOOK_SECRET", None)
    if not secret:
        return True  # skip if not configured

    received_sig = request.headers.get("X-HubSpot-Signature", "")
    expected_sig = hmac.new(
        secret.encode(), request.body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(received_sig, expected_sig)


@csrf_exempt
def hubspot_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    if not verify_signature(request):
        return HttpResponseForbidden("Invalid signature")

    try:
        payload = json.loads(request.body)

        for event in payload:
            if event.get("object") == "deal":
                deal_id = str(event.get("objectId"))

                for change in event.get("changes", []):
                    if change.get("property") == "dealstage":
                        new_stage = change.get("value")

                        order = Orders.objects.filter(hubspot_deal_id=deal_id).first()
                        if order:
                            order.deal_stage = new_stage
                            order.save()

        return JsonResponse({"status": "success"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)