"""Regression net for the second-person authorization throttle.

`_verify_supervisor` (Tracker/viewsets/mes_lite.py) rate-limits the
supervisor password check so a shared shop-floor terminal isn't a
brute-force oracle. It had **no tests at all** — nothing in the suite
referenced `override_throttled` or the `tgate_fail` cache key, and
`test_training.test_qualified_ignores_stray_bad_credentials` only asserts a
*qualified* operator never reaches the throttle.

These tests exist so the mechanism can be safely extracted into a shared
`verify_second_person` helper (for the FPI co-signature gate). Without them,
a mistyped cache-key format during extraction would silently disable
rate-limiting while every other test stayed green.

They pin the observable contract:
  * the cap trips at 5 failed authentications, with 429 + `override_throttled`
  * only failed *authentication* counts — a correct password that fails a
    later check (self, missing permission) must not consume budget
  * a successful authorization clears the counter
  * counters are isolated per tenant

**Cache hygiene.** The counter lives in the real Redis cache (settings uses
RedisCache), shared across the `--parallel` workers. These tests do NOT call
`cache.clear()` — django-redis can implement it as FLUSHDB, which would wipe
a developer's entire local cache. Isolation instead comes from the key
including the tenant id, and every test class creating its own Tenant; the
specific keys are deleted in tearDown for tidiness.
"""
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    Parts, PartTypes, ProcessStep, Processes, Steps, Tenant, TrainingRequirement,
    TrainingType, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin

User = get_user_model()

# Mirrors the literal in mes_lite._verify_supervisor. If the extraction
# changes the key format, these tests fail — which is the point.
THROTTLE_PREFIX = 'tgate_fail'
FAIL_CAP = 5


def throttle_key(tenant, email):
    return f"{THROTTLE_PREFIX}:{tenant.id}:{email.lower()}"


class SecondPersonThrottleTests(TenantContextMixin, TestCase):
    """Drives the throttle through the real endpoint (POST /api/StepExecutions/),
    the same route `test_training.TrainingGateViewSetTests` uses."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Throttle T", slug="throttle-t")
        self.set_tenant_context(self.tenant)

        self.operator = User.objects.create_user(
            username="thr-op", email="op@thr.test", password="x", tenant=self.tenant,
        )
        self.supervisor = User.objects.create_user(
            username="thr-sup", email="sup@thr.test", password="suppass",
            tenant=self.tenant,
        )
        # Valid login, no override permission — used to prove a correct
        # password that fails the *permission* check costs no budget.
        self.coworker = User.objects.create_user(
            username="thr-cow", email="cow@thr.test", password="cowpass",
            tenant=self.tenant,
        )

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Thr Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Thr Process", part_type=self.pt,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Thr Op", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-THR-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
            process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-THR-1", part_type=self.pt,
            work_order=self.wo, step=self.step,
        )
        # A training requirement nobody satisfies, so the gate always fires and
        # the supervisor is actually consulted.
        tt = TrainingType.objects.create(
            name="Thr Cert", validity_period_days=365, tenant=self.tenant,
        )
        TrainingRequirement.objects.create(
            training_type=tt, step=self.step, tenant=self.tenant,
        )

        self._grant(self.operator, "add_stepexecution", "change_stepexecution",
                    "view_stepexecution", "full_tenant_access", group="thr-ops")
        self._grant(self.supervisor, "add_stepexecution", "change_stepexecution",
                    "view_stepexecution", "override_training_gate",
                    "full_tenant_access", group="thr-sups")
        self._grant(self.coworker, "view_stepexecution", "full_tenant_access",
                    group="thr-cows")

        self._keys = set()

    def tearDown(self):
        # Targeted cleanup — never cache.clear(), see module docstring.
        for k in self._keys:
            cache.delete(k)
        super().tearDown()

    # -- helpers ------------------------------------------------------------

    def _grant(self, user, *codenames, group):
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole
        grp, _ = TenantGroup.objects.get_or_create(
            tenant=self.tenant, name=group, defaults={"is_custom": True},
        )
        grp.permissions.add(*Permission.objects.filter(codename__in=codenames))
        UserRole.objects.get_or_create(user=user, group=grp)
        user.clear_permission_cache(self.tenant)

    def _client(self, user):
        from rest_framework.test import APIClient
        c = APIClient()
        c.force_authenticate(user=user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def _start(self, actor, **extra):
        body = {"part": str(self.part.id), "step": str(self.step.id),
                "status": "IN_PROGRESS"}
        body.update(extra)
        return self._client(actor).post("/api/StepExecutions/", body, format="json")

    def _bad_password_attempt(self, email="sup@thr.test"):
        self._keys.add(throttle_key(self.tenant, email))
        return self._start(self.operator, override_email=email,
                           override_password="wrong", override_reason="line-down")

    def _counter(self, email="sup@thr.test"):
        return cache.get(throttle_key(self.tenant, email)) or 0

    # -- the contract -------------------------------------------------------

    def test_failed_auth_increments_the_counter(self):
        self.assertEqual(self._counter(), 0)
        resp = self._bad_password_attempt()
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "override_auth_failed")
        self.assertEqual(self._counter(), 1)

    def test_cap_trips_at_five_with_429(self):
        for i in range(FAIL_CAP):
            resp = self._bad_password_attempt()
            self.assertEqual(resp.status_code, 403, f"attempt {i + 1}: {resp.content}")
        self.assertEqual(self._counter(), FAIL_CAP)

        # The 6th is refused before the password is even checked.
        resp = self._bad_password_attempt()
        self.assertEqual(resp.status_code, 429, resp.content)
        self.assertEqual(resp.data["code"], "override_throttled")

    def test_throttle_blocks_even_the_correct_password(self):
        """Once tripped, a supervisor who now types it right is still refused —
        that is what makes it a throttle rather than a hint."""
        for _ in range(FAIL_CAP):
            self._bad_password_attempt()
        resp = self._start(self.operator, override_email="sup@thr.test",
                           override_password="suppass", override_reason="line-down")
        self.assertEqual(resp.status_code, 429, resp.content)
        self.assertEqual(resp.data["code"], "override_throttled")

    def test_throttled_attempts_do_not_extend_the_lockout(self):
        """The cap check returns before the increment, so hammering a locked
        account must not push the counter past the cap (and so must not keep
        renewing the TTL)."""
        for _ in range(FAIL_CAP):
            self._bad_password_attempt()
        for _ in range(3):
            self._bad_password_attempt()
        self.assertEqual(self._counter(), FAIL_CAP)

    def test_successful_authorization_clears_the_counter(self):
        for _ in range(FAIL_CAP - 1):
            self._bad_password_attempt()
        self.assertEqual(self._counter(), FAIL_CAP - 1)

        resp = self._start(self.operator, override_email="sup@thr.test",
                           override_password="suppass",
                           override_reason="trainee supervised")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self._counter(), 0)

    def test_missing_permission_does_not_consume_budget(self):
        """A correct password that fails a *later* check is not a failed
        authentication. Charging it would let a wrong-person mistake lock out
        the right person."""
        self._keys.add(throttle_key(self.tenant, "cow@thr.test"))
        resp = self._start(self.operator, override_email="cow@thr.test",
                           override_password="cowpass", override_reason="ok?")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "override_not_permitted")
        self.assertEqual(self._counter("cow@thr.test"), 0)

    def test_self_authorization_does_not_consume_budget(self):
        self._keys.add(throttle_key(self.tenant, "sup@thr.test"))
        resp = self._start(self.supervisor, override_email="sup@thr.test",
                           override_password="suppass", override_reason="me")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "override_self")
        self.assertEqual(self._counter(), 0)

    def test_counter_is_keyed_per_supervisor_email(self):
        for _ in range(FAIL_CAP):
            self._bad_password_attempt("sup@thr.test")
        self.assertEqual(self._counter("sup@thr.test"), FAIL_CAP)
        # A different authorizer identity has its own budget.
        self.assertEqual(self._counter("cow@thr.test"), 0)

    def test_counter_is_isolated_per_tenant(self):
        """The key embeds the tenant id — which is also what makes these tests
        safe to run in parallel against one shared Redis."""
        other = Tenant.objects.create(name="Throttle U", slug="throttle-u")
        for _ in range(FAIL_CAP):
            self._bad_password_attempt()
        self.assertEqual(self._counter(), FAIL_CAP)
        self.assertEqual(cache.get(throttle_key(other, "sup@thr.test")) or 0, 0)
