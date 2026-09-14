"""
Tests for PickListAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape tests verifying qty_required = qty_per_assembly × qty_to_produce
"""
from django.test import SimpleTestCase, TestCase

from Tracker.reports.adapters.pick_list import (
    PickListAdapter,
    PickListContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin
from Tracker.tests.base import TenantContextMixin


class TestPickListAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = PickListAdapter
    fixture_name = "pick_list_sample"

    def test_cross_tenant_id_is_rejected(self):
        # A real cross-tenant probe requires DB state (two tenants, two
        # users, a WorkOrder in tenant A submitted by a user in tenant B).
        # That is exercised by integration tests; here we confirm the
        # param serializer's validate_id() method enforces the tenant filter.
        # Override this with a TransactionTestCase-based test when a
        # multi-tenant fixture is available.
        self.skipTest(
            "Cross-tenant isolation is enforced by the tenant= filter in "
            "PickListParamsSerializer.validate_id() and the ORM query in "
            "build_context(). Full probe requires DB state - see integration tests."
        )


class PickListFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def setUp(self):
        self._mixin = TestPickListAdapter()
        self._fixture = self._mixin._load_fixture()

    def test_total_line_count_matches_items(self):
        """total_line_count must equal the number of items in the list."""
        self.assertEqual(
            self._fixture["total_line_count"],
            len(self._fixture["items"]),
            "fixture total_line_count does not match len(items)",
        )

    def test_qty_required_equals_qty_per_assembly_times_wo_qty(self):
        """Every item's qty_required must equal qty_per_assembly × qty_to_produce."""
        from decimal import Decimal
        from Tracker.reports.adapters.pick_list import _fmt_qty

        wo_qty = self._fixture["qty_to_produce"]
        for item in self._fixture["items"]:
            expected = _fmt_qty(Decimal(item["qty_per_assembly"]) * Decimal(wo_qty))
            self.assertEqual(
                item["qty_required"],
                expected,
                f"Item find_number={item['find_number']!r}: qty_required "
                f"{item['qty_required']!r} != {expected!r} "
                f"(qty_per_assembly={item['qty_per_assembly']} × wo_qty={wo_qty})",
            )

    def test_fixture_has_at_least_one_optional_item(self):
        """Fixture must include at least one optional line to exercise that branch."""
        optional_items = [i for i in self._fixture["items"] if i["is_optional"]]
        self.assertGreater(
            len(optional_items),
            0,
            "fixture has no optional items - the OPT badge branch is not exercised",
        )

    def test_fixture_has_at_least_one_required_item(self):
        """Fixture must include at least one non-optional line."""
        required_items = [i for i in self._fixture["items"] if not i["is_optional"]]
        self.assertGreater(
            len(required_items),
            0,
            "fixture has no required items - all items are optional",
        )

    def test_fixture_has_multi_qty_line(self):
        """At least one line should have qty_per_assembly > 1 to exercise multiplication."""
        multi = [
            i for i in self._fixture["items"]
            if i["qty_per_assembly"] not in ("1", "1.0")
        ]
        self.assertGreater(
            len(multi),
            0,
            "fixture has no multi-qty lines - qty_required multiplication is not exercised",
        )

    def test_context_model_validates_cleanly(self):
        """PickListContext must accept the fixture without raising."""
        try:
            ctx = PickListContext(**self._fixture)
        except Exception as exc:
            self.fail(f"PickListContext validation failed: {exc}")
        self.assertEqual(ctx.total_line_count, len(ctx.items))
        self.assertEqual(ctx.qty_to_produce, self._fixture["qty_to_produce"])


class PickListRouteScopeTests(TenantContextMixin, TestCase):
    """A requisition lists what THIS job consumes, not every branch's parts.

    `BOMLine.consumed_at_step` pegs a line to the operation that consumes it, and a
    process may carry rework/alternate branches a released job will not run. Exploding
    the whole BOM regardless of route means the crib hands over parts for operations
    that are not going to happen — and the picker has no way to know which.

    Currently latent rather than live: no authored BOM pegs a line to an off-route step
    yet. It becomes live the first time one does, and the reman branched-process work
    depends on this resolution being right.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Material, PartTypes, Processes, ProcessStep, StepEdge, Steps,
            Tenant, WorkOrder, WorkOrderStatus,
        )
        self.tenant = Tenant.objects.create(name="Pick", slug="pick-route", tier="PRO")
        self.set_tenant_context(self.tenant)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Reman", part_type=self.pt)

        def _step(name, order):
            s = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name=name,
                                     step_type="TASK")
            ProcessStep.objects.create(process=self.process, step=s, order=order)
            return s

        self.wash = _step("Wash", 1)
        self.test = _step("Test", 2)
        # Reachable only by the ALTERNATE (fail) edge — the rework bay. A released job
        # does not plan to go here.
        self.rework = _step("Rework", 3)

        StepEdge.objects.create(process=self.process, from_step=self.wash,
                                to_step=self.test, edge_type="DEFAULT")
        StepEdge.objects.create(process=self.process, from_step=self.test,
                                to_step=self.rework, edge_type="ALTERNATE")

        self.seal = Material.objects.create(tenant=self.tenant, name="Seal kit")
        self.shim = Material.objects.create(tenant=self.tenant, name="Rework shim")
        self.oil = Material.objects.create(tenant=self.tenant, name="Test oil")

        self.bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt,
                                      revision="A", status="RELEASED")
        BOMLine.objects.create(tenant=self.tenant, bom=self.bom, material=self.seal,
                               quantity=1, source='BUY', consumed_at_step=self.wash)
        BOMLine.objects.create(tenant=self.tenant, bom=self.bom, material=self.shim,
                               quantity=1, source='BUY', consumed_at_step=self.rework)
        # Pegged to nothing: consumed somewhere unspecified, so always in scope.
        BOMLine.objects.create(tenant=self.tenant, bom=self.bom, material=self.oil,
                               quantity=1, source='BUY')

        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-ROUTE", quantity=2, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)

    def _items(self):
        ctx = PickListAdapter().build_context(
            {"id": self.wo.id}, user=None, tenant=self.tenant)
        return {i.component_name: i for i in ctx.items}

    def test_a_line_on_a_rework_branch_is_not_picked(self):
        item = self._items()["Rework shim"]
        self.assertEqual(item.not_picked_reason, "not on this job's route")
        self.assertEqual(item.lots, "")
        self.assertEqual(item.storage_location, "")

    def test_an_off_route_line_still_appears_on_the_sheet(self):
        """It must not silently vanish. A line that disappears reads as a BOM that
        never had it; a line marked not-picked reads as a decision."""
        self.assertIn("Rework shim", self._items())

    def test_lines_on_the_route_are_picked_normally(self):
        self.assertEqual(self._items()["Seal kit"].not_picked_reason, "")

    def test_an_unpegged_line_is_always_in_scope(self):
        """`consumed_at_step` null means the whole parent consumes it — there is no
        branch to be off."""
        self.assertEqual(self._items()["Test oil"].not_picked_reason, "")

    def test_nothing_is_filtered_when_the_route_cannot_be_resolved(self):
        """A process with no authored steps resolves no route. Under-picking silently is
        a worse failure than over-picking: the picker cannot see an absence."""
        from Tracker.models import ProcessStep
        ProcessStep.objects.filter(process=self.process).delete()
        items = self._items()
        self.assertEqual(items["Rework shim"].not_picked_reason, "")
        self.assertEqual(len(items), 3)
