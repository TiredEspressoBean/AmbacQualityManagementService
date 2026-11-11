"""ViewSet mixin for the work-start gates' supervisor escape.

Every start path (Start Work / claim, creating or PATCHing a visit to IN_PROGRESS,
starting a load) runs the one start decision (`services/mes/gates.decide_start`). Its
supervisor-overridable refusals — training, the revisit rule, reassignment — are
cleared by a second person signing in inline; this mixin holds that request-layer
handling so every start path offers the same escape.
"""
from rest_framework import status
from rest_framework.response import Response

from .second_person import SecondPersonMixin


class StartGateMixin(SecondPersonMixin):
    """Adds `_gated_start()` and the supervisor verification it escalates to.

    Requires `self.tenant` (from `TenantScopedMixin`)."""

    # Wording kept verbatim from before this gate was extracted into
    # `SecondPersonMixin` — it is already on screen in production, and the
    # extraction must not silently reword it. Codes stay `override_*` for the
    # same reason: the frontend handles those.
    _SUPERVISOR_MESSAGES = {
        'auth_failed': 'Supervisor authorization failed - check the email and password.',
        'self': 'The authorizing supervisor must be a different person than the operator.',
        'not_permitted': 'That user is not authorized to override.',
    }

    def _verify_supervisor(self, request):
        """Verify a second-person supervisor from `override_email`/`override_password`
        WITHOUT logging them in. Shared by the training gate and the reassignment
        check, and memoized per request so one supervisor login clears both (and
        the throttle only decrements once).

        Delegates to `SecondPersonMixin`; behaviour pinned by
        `Tracker/tests/test_second_person_throttle.py`.

        Returns ``(authorizer, error)``:
          - ``(User, None)``  — a *different*, active user who holds
            `override_training_gate` in this tenant.
          - ``(None, (detail, code, http_status))`` — creds supplied but invalid.
          - ``(None, None)`` — no creds supplied at all.
        """
        return self.verify_second_person(
            request,
            permission='override_training_gate',
            throttle_prefix='tgate_fail',
            code_prefix='override',
            email_field='override_email',
            password_field='override_password',
            messages=self._SUPERVISOR_MESSAGES,
        )

    def _supervisor_error_response(self, err):
        """Translate a `_verify_supervisor` failure tuple → Response."""
        return self.second_person_error_response(err)

    def _start_gate_error_response(self, exc):
        """Translate a work-start domain error (`services/mes/lifecycle`) → Response."""
        from Tracker.services.mes.lifecycle import (
            NotQualified, NeedsReassignment, OverrideReasonRequired, RevisitRefused,
        )
        if isinstance(exc, NeedsReassignment):
            who = (exc.current_operator.get_full_name()
                   or exc.current_operator.get_username())
            return Response({
                'detail': f"Assigned to {who}. A supervisor must reassign it.",
                'code': 'assigned_to_other',
                'assigned_to_name': who,
            }, status=status.HTTP_409_CONFLICT)
        if isinstance(exc, NotQualified):
            return Response({
                'detail': 'You are not qualified for this step.',
                'code': 'training_not_authorized',
                'missing': exc.missing,
            }, status=status.HTTP_409_CONFLICT)
        if isinstance(exc, RevisitRefused):
            # The step's revisit rule (DIFFERENT / ROLE) on a repeat visit.
            return Response({'detail': exc.detail, 'code': 'revisit_rule'},
                            status=status.HTTP_409_CONFLICT)
        if isinstance(exc, OverrideReasonRequired):
            body = {'detail': exc.detail, 'code': 'override_reason_required'}
            if exc.missing is not None:
                body['missing'] = exc.missing
            return Response(body, status=status.HTTP_400_BAD_REQUEST)
        raise exc

    def _gated_start(self, request, apply):
        """Run a work-start op, escalating to a second-person supervisor override
        ONLY when the unauthorized attempt is actually blocked.

        `apply(authorizer)` calls the start decision. We try it with no authorizer
        first: if it succeeds the operator was authorized and no supervisor is
        consulted (so stray/invalid override creds on an otherwise-authorized start
        are ignored, and the password throttle isn't touched). Only on a
        StartGateError do we verify a supervisor and retry. Returns
        ``(result, error_response)`` — exactly one is non-None.
        """
        from Tracker.services.mes.lifecycle import StartGateError
        try:
            return apply(None), None
        except StartGateError as first:
            authorizer, verr = self._verify_supervisor(request)
            if verr is not None:
                return None, self._supervisor_error_response(verr)
            if authorizer is None:
                # No credentials supplied → return the original block.
                return None, self._start_gate_error_response(first)
            try:
                return apply(authorizer), None
            except StartGateError as second:
                return None, self._start_gate_error_response(second)
