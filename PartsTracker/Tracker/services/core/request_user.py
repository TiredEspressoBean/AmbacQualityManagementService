"""Who made the current request, for work done after a signal or on commit where the
caller can't pass the user along — e.g. a submitted change's draft refreshed after an
edit, whose history names who edited (change_control/draft_refresh.py). None outside a
request (a task, a script).
"""
from __future__ import annotations

from contextvars import ContextVar

_user: ContextVar = ContextVar('request_user', default=None)


def current_user():
    return _user.get()


class RequestUserMiddleware:
    """Sets the request's authenticated user for the request's duration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        token = _user.set(user if getattr(user, 'is_authenticated', False) else None)
        try:
            return self.get_response(request)
        finally:
            _user.reset(token)
