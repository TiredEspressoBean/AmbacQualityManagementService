"""
Tests for WorkOrderTravelerAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape tests (total_operations matches, control tags
  and outside-process branch exercised)
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.work_order_traveler import (
    WorkOrderTravelerAdapter,
    WorkOrderTravelerContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestWorkOrderTravelerAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = WorkOrderTravelerAdapter
    fixture_name = "work_order_traveler_sample"

    def test_cross_tenant_id_is_rejected(self):
        # A real cross-tenant probe requires DB state (two tenants, two
        # users, a WorkOrder in tenant A submitted by a user in tenant B).
        # Isolation is enforced by the tenant= filter in
        # WorkOrderTravelerParamsSerializer.validate_id() and the ORM query
        # in build_context(); the full probe lives in integration tests.
        self.skipTest(
            "Cross-tenant isolation is enforced by the tenant= filter in "
            "WorkOrderTravelerParamsSerializer.validate_id() and the ORM query "
            "in build_context(). Full probe requires DB state - see integration tests."
        )


class WorkOrderTravelerFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def setUp(self):
        self._mixin = TestWorkOrderTravelerAdapter()
        self._fixture = self._mixin._load_fixture()

    def test_total_operations_matches_operations(self):
        """total_operations must equal the number of routing rows."""
        self.assertEqual(
            self._fixture["total_operations"],
            len(self._fixture["operations"]),
            "fixture total_operations does not match len(operations)",
        )

    def test_fixture_has_outside_process_op(self):
        """Fixture must include an outside-process op to exercise the OSP branch."""
        osp = [o for o in self._fixture["operations"] if o["is_outside_process"]]
        self.assertGreater(
            len(osp), 0,
            "fixture has no outside-process op - the OSP branch is not exercised",
        )

    def test_fixture_has_op_with_controls_and_op_without(self):
        """Both the controls-present and empty-controls branches must render."""
        with_controls = [o for o in self._fixture["operations"] if o["controls"]]
        without_controls = [o for o in self._fixture["operations"] if not o["controls"]]
        self.assertGreater(len(with_controls), 0, "no op with control tags")
        self.assertGreater(len(without_controls), 0, "no op with empty controls")

    def test_context_model_validates_cleanly(self):
        """WorkOrderTravelerContext must accept the fixture without raising."""
        try:
            ctx = WorkOrderTravelerContext(**self._fixture)
        except Exception as exc:  # noqa: BLE001 — surface any validation error
            self.fail(f"WorkOrderTravelerContext validation failed: {exc}")
        self.assertEqual(ctx.total_operations, len(ctx.operations))

    def test_fixture_actuals_default_blank(self):
        """The job-release fixture leaves per-op actuals + serial unset (blank form)."""
        ctx = WorkOrderTravelerContext(**self._fixture)
        self.assertIsNone(ctx.serial)
        for op in ctx.operations:
            self.assertIsNone(op.operator)
            self.assertIsNone(op.inspector)
            self.assertIsNone(op.acc_rej)


class WorkOrderTravelerAsBuiltUnitTests(SimpleTestCase):
    """Pure-function tests for the as-built history helpers (no DB)."""

    def _adapter(self):
        return WorkOrderTravelerAdapter()

    def test_short_name_and_date_formatting(self):
        from types import SimpleNamespace
        from Tracker.reports.adapters.work_order_traveler import (
            _short_name, _short_date, _join_person_date,
        )

        class U:
            def __init__(self, full, username="", email=""):
                self._full, self.username, self.email = full, username, email
            def get_full_name(self):
                return self._full

        self.assertEqual(_short_name(U("Mike Rogers")), "Mike R.")
        self.assertEqual(_short_name(U("", username="lisa.docs")), "lisa.docs")
        self.assertEqual(_short_name(U("", email="a@b.com")), "a")
        self.assertIsNone(_short_name(None))
        self.assertEqual(_short_date(SimpleNamespace(month=7, day=9)), "7/9")
        self.assertIsNone(_short_date(None))
        self.assertEqual(_join_person_date(U("Mike Rogers"), SimpleNamespace(month=7, day=9)), "Mike R. · 7/9")

    def test_step_actuals_maps_verdict_and_keeps_full_remark(self):
        from types import SimpleNamespace
        adapter = self._adapter()

        class U:
            def get_full_name(self):
                return "Sarah Chen"

        ex = SimpleNamespace(
            completed_by=None, assigned_to=U(),
            exited_at=None, started_at=SimpleNamespace(month=7, day=14), entered_at=None,
        )
        long_desc = "Nozzle tip scoring found during visual inspection - annotate required"
        qr_fail = SimpleNamespace(
            verified_by=None, detected_by=U(),
            created_at=SimpleNamespace(month=7, day=15), status="FAIL", description=long_desc,
        )
        operator, inspector, acc_rej, remarks = adapter._step_actuals(ex, qr_fail)
        self.assertEqual(operator, "Sarah C. · 7/14")
        self.assertEqual(inspector, "Sarah C. · 7/15")
        self.assertEqual(acc_rej, "REJ")
        # Full text is preserved (no truncation) — the Remarks box grows to fit;
        # clipping a nonconformance finding mid-sentence loses traceability.
        self.assertEqual(remarks, long_desc)

        qr_pass = SimpleNamespace(
            verified_by=None, detected_by=U(),
            created_at=SimpleNamespace(month=7, day=15), status="PASS", description="ok",
        )
        _, _, acc_rej_pass, remarks_pass = adapter._step_actuals(None, qr_pass)
        self.assertEqual(acc_rej_pass, "ACC")
        self.assertEqual(remarks_pass, "ok")

        # No execution + no report → all blank.
        self.assertEqual(adapter._step_actuals(None, None), (None, None, None, None))
