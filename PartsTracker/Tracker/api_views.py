import json

from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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


@extend_schema(operation_id="get_user_api_token",
               description="Get or create an API token for the current session-authenticated user", request=None,
               responses={200: {"type": "object",
                                "properties": {"token": {"type": "string", "description": "The API token"},
                                               "created": {"type": "boolean",
                                                           "description": "Whether a new token was created"}}},
                          401: {"description": "Authentication required"},
                          500: {"description": "Internal server error"}})
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # overrides global defaults (no DjangoModelPermissions here)
@authentication_classes([SessionAuthentication])  # use the browser session
@csrf_protect  # POST must include X-CSRFToken
def get_user_api_token(request):
    """
    Get or create an API token for the current session-authenticated user.
    This endpoint allows frontend to get API tokens for making authenticated API calls.
    """
    try:
        # Get or create a token for the user
        token, created = Token.objects.get_or_create(user=request.user)

        return Response({"token": token.key, "created": created}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
