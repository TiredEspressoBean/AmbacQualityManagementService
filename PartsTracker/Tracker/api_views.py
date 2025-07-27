import json

from django.contrib.auth import login, logout, authenticate
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.http import JsonResponse



@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user = authenticate(username=data["username"], password=data["password"])
        if user:
            login(request, user)
            return JsonResponse({"success": True})
        return JsonResponse({"success": False}, status=401)

def logout_view(request):
    logout(request)
    return JsonResponse({"success": True})
