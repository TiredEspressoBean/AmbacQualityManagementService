"""ViewSet mixin for second-person (co-signature) authorization.

Thin request-layer wrapper over `services.core.second_person.verify_second_person`
— it pulls credentials off `request.data`, memoizes per request, and translates
a failure tuple into a DRF `Response`. The decision logic lives in the service,
per the "viewsets delegate" rule.
"""
from rest_framework.response import Response

from Tracker.services.core.second_person import verify_second_person


class SecondPersonMixin:
    """Adds `verify_second_person()` / `second_person_error_response()`.

    Requires `self.tenant` (from `TenantScopedMixin`).
    """

    def verify_second_person(
        self,
        request,
        *,
        permission,
        throttle_prefix,
        code_prefix,
        email_field,
        password_field,
        fail_cap=5,
        fail_ttl=900,
        messages=None,
    ):
        """Verify a second person from `request.data`, memoized per request.

        Memoized so one co-signature can satisfy several gates in a single
        request without being charged to the throttle more than once — the
        training gate and the reassignment check both consult it on one POST.

        The cache is a **dict keyed by (permission, throttle_prefix)**, not a
        single attribute. With one attribute, a request that consulted two
        different gates would get the first gate's answer for the second — i.e.
        a person authorized for one thing would silently pass as authorized for
        another. That is the whole reason this is a dict.

        Returns `(authorizer, error)`; see the service's module docstring.
        """
        cache_key = (permission, throttle_prefix)
        store = getattr(self, '_second_person_cache', None)
        if store is None:
            store = {}
            self._second_person_cache = store
        if cache_key in store:
            return store[cache_key]

        result = verify_second_person(
            tenant=self.tenant,
            actor=request.user,
            email=request.data.get(email_field) or '',
            password=request.data.get(password_field) or '',
            permission=permission,
            throttle_prefix=throttle_prefix,
            code_prefix=code_prefix,
            fail_cap=fail_cap,
            fail_ttl=fail_ttl,
            messages=messages,
        )
        store[cache_key] = result
        return result

    def second_person_error_response(self, err):
        """Translate a `verify_second_person` failure tuple → Response."""
        detail, code, http_status = err
        return Response({'detail': detail, 'code': code}, status=http_status)
