"""
Custom exceptions and exception handler for consistent API responses.

HTTP Status Code Standards:
- 400 Bad Request: Invalid input, validation errors, missing required fields
- 401 Unauthorized: Not authenticated (no valid credentials provided)
- 403 Forbidden: Authenticated but not authorized (lacks permission)
- 404 Not Found: Resource doesn't exist or not accessible in current scope
- 409 Conflict: Action conflicts with current state (e.g., duplicate)
- 422 Unprocessable Entity: Valid syntax but semantic errors
"""

from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied


class TenantContextRequired(APIException):
    """Raised when a request requires tenant context but none is available."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This endpoint requires a tenant context. Provide X-Tenant-ID header.'
    default_code = 'tenant_context_required'


class TenantAccessDenied(APIException):
    """Raised when user doesn't have access to the requested tenant."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have permission to access this tenant."
    default_code = 'tenant_access_denied'


class TenantSuspended(APIException):
    """Raised when tenant is suspended and cannot perform the operation."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'This tenant is suspended. Please contact support.'
    default_code = 'tenant_suspended'


class ResourceNotFound(APIException):
    """Raised when a requested resource is not found within tenant scope."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'


class ResourceConflict(APIException):
    """Raised when action conflicts with current state (e.g., duplicate slug)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This action conflicts with the current state.'
    default_code = 'conflict'


def custom_exception_handler(exc, context):
    """
    Custom exception handler that ensures consistent HTTP status codes.

    Key behaviors:
    - NotAuthenticated always returns 401 (not 403)
    - AuthenticationFailed always returns 401
    - PermissionDenied always returns 403
    - Http404 always returns 404

    Response format:
    {
        "detail": "Human-readable error message",
        "code": "machine_readable_error_code"  # optional
    }
    """
    # Handle Django's PermissionDenied
    if isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied(detail=str(exc) if str(exc) else None)

    # Handle Django's Http404
    if isinstance(exc, Http404):
        exc = ResourceNotFound(detail=str(exc) if str(exc) else None)

    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Ensure NotAuthenticated returns 401, not 403
        # DRF returns 403 for NotAuthenticated when using SessionAuthentication
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            response.status_code = status.HTTP_401_UNAUTHORIZED
            # Add WWW-Authenticate header for proper 401 response
            response['WWW-Authenticate'] = 'Bearer realm="api"'

        # Add error code to response if available
        if hasattr(exc, 'default_code') and 'code' not in response.data:
            response.data['code'] = exc.default_code
        elif hasattr(exc, 'get_codes'):
            codes = exc.get_codes()
            if isinstance(codes, str):
                response.data['code'] = codes
            elif isinstance(codes, dict) and len(codes) == 1:
                # For single-field errors, extract the code
                response.data['code'] = list(codes.values())[0]
                if isinstance(response.data['code'], list):
                    response.data['code'] = response.data['code'][0]

    return response
