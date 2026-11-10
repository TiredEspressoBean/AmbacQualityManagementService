"""Receiving fixes from the quality bug hunt, round 2 (2026-11-10).

- N9 / R1: a DWI reading on a receiving lot leaves the verdict to the sampling plan
  (defectives vs Ac/Re once n units are in), and the decided lot counts for Z1.4
  switching.
- N13: confirming a whole-lot reject request closes the inspection.
- N3: a manual hold being PLACED isn't printed as a hold released.
- N14: Accept on an unfinished sample takes a reason and an approval; the report keeps
  no verdict.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_receiving_inspection import _ReceivingFixtureMixin
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id
from Tracker.services.qms import receiving_inspection as ri

User = get_user_model()


class DwiLotVerdictTests(_ReceivingFixtureMixin, TenantTestCase):
    """N9 / R1."""

    def setUp(self):
        super().setUp()
        self._build_fixtures()
        # Lot 100, level II → code F (n=20); AQL 2.5 → Ac 1, Re 2.
        self.ruleset.strategy = "Z14"
        self.ruleset.aql = Decimal("2.5")
        self.ruleset.save(update_fields=["strategy", "aql"])
        from Tracker.models import Substep
        self.substep = Substep.objects.create(
            tenant=self.tenant_a, step=self.recv_step, title="Inspect", order=1,
            is_inspection_point=True)

    def _read(self, lot, unit, verdict):
        from Tracker.services.qms.inline_capture import record_dwi_measurement
        record_dwi_measurement(
            step_execution=ri.receiving_execution(lot), substep=self.substep,
            measurement_definition=self.char, value_string=verdict,
            recorded_by=self.user_a, sample_number=unit)

    def test_one_defective_within_ac_does_not_fail_the_lot(self):
        lot = self._make_lot()
        report = ri.open_inspection(lot, self.user_a)
        self.assertEqual((report.sample_size, report.accept_number, report.reject_number), (20, 1, 2))
        self._read(lot, 1, "FAIL")
        report.refresh_from_db()
        self.assertEqual(report.status, "PENDING", "Ac is 1: one defective is within the plan")

    def test_one_good_reading_does_not_pass_the_lot(self):
        lot = self._make_lot()
        report = ri.open_inspection(lot, self.user_a)
        self._read(lot, 1, "PASS")
        report.refresh_from_db()
        self.assertEqual(report.status, "PENDING", "1 of 20 units isn't a verdict")

    def test_the_full_sample_decides_and_counts_for_switching(self):
        from Tracker.models import SamplingSeverityState
        lot = self._make_lot()
        report = ri.open_inspection(lot, self.user_a)
        self._read(lot, 1, "FAIL")
        for unit in range(2, 21):
            self._read(lot, unit, "PASS")
        report.refresh_from_db()
        self.assertEqual(report.status, "PASS")
        state = SamplingSeverityState.objects.get(step=self.recv_step)
        self.assertEqual(state.lots_in_regime, 1, "the decided lot counts once")

    def test_reaching_re_fails_it(self):
        lot = self._make_lot()
        report = ri.open_inspection(lot, self.user_a)
        self._read(lot, 1, "FAIL")
        self._read(lot, 2, "FAIL")
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")


class DwiStatusAndPlanTests(_ReceivingFixtureMixin, TenantTestCase):
    """Walk 2026-11-10 follow-ups: the DWI status capture doesn't decide a lot; the
    page shows the frozen plan; AQL below the tables is refused, not snapped up."""

    def setUp(self):
        super().setUp()
        self._build_fixtures()

    def test_a_substep_status_doesnt_decide_a_lot(self):
        from Tracker.services.dwi.operator_capture import _apply_status
        lot = self._make_lot()
        report = ri.open_inspection(lot, self.user_a)
        _apply_status(report, {"status": "PASS"})
        report.refresh_from_db()
        self.assertEqual(report.status, "PENDING")
        report.status = "FAIL"
        report.save(update_fields=["status"])
        _apply_status(report, {"status": "PENDING"})  # was refused, losing the run
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")

    def test_aql_below_the_tables_is_refused(self):
        from Tracker.services.qms.acceptance_sampling import compute_sample_plan
        with self.assertRaises(ValueError):
            compute_sample_plan(lot_size=500, aql=0.010, inspection_level="II",
                                severity="NORMAL", strategy="Z14")

    def test_the_page_shows_the_frozen_plan(self):
        lot = self._make_lot()
        report = ri.open_inspection(lot, self.user_a)
        frozen = (report.sample_size, report.accept_number, report.reject_number)
        # The rule changes after the inspection opened.
        self.ruleset.strategy = "Z14"
        self.ruleset.aql = Decimal("6.5")
        self.ruleset.save(update_fields=["strategy", "aql"])
        self.assertNotEqual(ri.sample_plan_for_lot(lot).sample_size, frozen[0])
        from rest_framework.test import APIClient
        c = APIClient()
        c.force_authenticate(user=self.superuser)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        body = c.get(f"/api/MaterialLots/{lot.id}/sample_plan/").json()
        self.assertEqual((body["sample_size"], body["accept_number"], body["reject_number"]), frozen)


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, Tenant
        cls.tenant = Tenant.objects.create(name="Hunt", slug="receiving-hunt-1110")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.qa = User.objects.create_user(username="qam", email="qam@x.test", password="x",
                                              tenant=cls.tenant, is_staff=True)
            cls.qa.is_superuser = True
            cls.qa.save(update_fields=["is_superuser"])
            # No groups: holds no tenant permissions.
            cls.inspector = User.objects.create_user(username="insp", email="insp@x.test",
                                                     password="x", tenant=cls.tenant)
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal", unit_of_measure="EA")
            ri.create_standalone_receiving_plan(cls.seal)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.qa)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _lot(self, qty="500", lot_number="L-1"):
        resp = self.client.post("/api/MaterialLots/", {
            "lot_number": lot_number, "material": str(self.seal.id), "quantity": qty,
            "received_date": str(date.today()), "unit_of_measure": "EA",
            "supplier": str(self.acme.id)}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        from Tracker.models import MaterialLot
        return MaterialLot.objects.get(pk=resp.json()["id"])

    def _report(self, lot):
        return lot.quality_reports.order_by("-created_at").first()

    def _qa_group(self, *users):
        """A group holding the accept-incomplete authority (as QA Manager's does)."""
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole
        grp = TenantGroup.objects.create(tenant=self.tenant, name="QA", is_custom=True)
        grp.permissions.add(Permission.objects.get(codename="accept_incomplete_sample"))
        for u in users:
            UserRole.objects.create(user=u, group=grp)
            u.clear_permission_cache(self.tenant)
        return grp


class ConfirmWholeLotRejectTests(_Fixture):
    """N13."""

    def test_confirming_the_request_closes_the_inspection(self):
        from Tracker.services.qms.lot_reject import confirm_whole_lot_reject, reject_lot
        lot = self._lot()
        report = self._report(lot)
        reject_lot(report, self.inspector, whole_lot=True)
        self.assertIsNotNone(ri.receiving_execution(lot))
        confirm_whole_lot_reject(lot, self.qa)
        report.refresh_from_db()
        lot.refresh_from_db()
        self.assertEqual(lot.status, "REJECTED")
        self.assertEqual(report.status, "FAIL")
        self.assertIsNone(ri.receiving_execution(lot), "the receiving run is closed")


class HoldPlacementOnRecordTests(_Fixture):
    """N3."""

    def test_a_placed_hold_isnt_a_release(self):
        from Tracker.reports.adapters.receiving_inspection_record import _hold_releases
        lot = self._lot()
        ri.place_manual_hold(lot, self.qa, "Suspect plating")
        self.assertEqual(_hold_releases(lot), [])
        ri.release_hold(lot, self.qa, "Plating checked — fine")
        rows = _hold_releases(lot)
        self.assertEqual([r.what for r in rows], ["Hold released (Held by hand)"])


class PartialRejectRemainderTests(_Fixture):
    """Round-1 #3: a partial reject on an unfinished sample accepted the rest and
    stamped the report PASS though the inspection had found bad pieces."""

    def test_the_report_reads_fail(self):
        from Tracker.services.qms.lot_reject import reject_lot
        lot = self._lot()
        report = self._report(lot)
        self.assertEqual(report.status, "PENDING")
        _, _, outcome = reject_lot(report, self.qa, rejected_quantity=10)
        self.assertEqual(outcome, "PARTIAL")
        report.refresh_from_db()
        lot.refresh_from_db()
        self.assertEqual((report.status, lot.status), ("FAIL", "ACCEPTED"))


class StockHeldTwiceTests(_Fixture):
    """Round-3 #12: accepted stock held by hand, then a supplier hold added, went back
    through receiving when the supplier hold was released last."""

    def test_stock_returns_to_stock_whichever_hold_is_last(self):
        lot = self._lot()
        report = self._report(lot)
        report.status = "PASS"
        report.save(update_fields=["status"])
        ri.accept(report, self.qa)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")
        ri.place_manual_hold(lot, self.qa, "Suspect plating")
        # A supplier suspension doesn't touch stock held by hand.
        self.assertEqual(ri.hold_supplier_lots_at_dock(self.acme), [])
        # Even if it carries a second hold, releasing them in any order restores stock.
        from Tracker.services.qms import lot_holds
        lot.refresh_from_db()
        lot_holds.hold(lot, ri.HOLD_SUPPLIER_UNQUALIFIED)
        lot.refresh_from_db()
        ri.release_hold(lot, self.qa, "Plating fine", code="MANUAL")
        ri.release_hold(lot, self.qa, "Supplier requalified", code=ri.HOLD_SUPPLIER_UNQUALIFIED)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")

    def test_inbox_plan_badge_is_the_frozen_plan(self):
        """Round-3 #13."""
        from Tracker.services.qms.inspection_inbox import _plan_badge
        lot = self._lot()
        report = self._report(lot)
        self.assertEqual(_plan_badge(lot), f"n={report.sample_size} · Ac {report.accept_number or 0}")


class AcceptIncompleteTests(_Fixture):
    """N14 (user decision 2026-11-10)."""

    def test_plain_accept_of_an_unfinished_sample_is_refused(self):
        lot = self._lot()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/accept/")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("isn't complete", resp.json()["detail"])
        lot.refresh_from_db()
        self.assertEqual(lot.status, "AWAITING_INSPECTION")

    def test_a_reason_is_required(self):
        lot = self._lot()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/accept_incomplete/",
                                {"reason": "short"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_an_inspector_s_request_waits_then_qa_approves_it(self):
        from Tracker.services.core.approval import submit_approval_response
        approver = User.objects.create_user(username="qa2", email="qa2@x.test", password="x",
                                            tenant=self.tenant)
        self._qa_group(approver)
        lot = self._lot()
        report = self._report(lot)
        outcome, approval = ri.request_accept_incomplete(
            report, self.inspector, "Line down; 3 of 5 checked clean, rest after the run")
        self.assertEqual(outcome, "REQUESTED")
        lot.refresh_from_db()
        self.assertEqual(lot.status, "AWAITING_INSPECTION", "it waits under inspection")
        self.assertTrue(approval.can_approve(approver))
        self.assertFalse(approval.can_approve(self.inspector))
        # A second request while one waits is refused.
        with self.assertRaises(ValueError):
            ri.request_accept_incomplete(report, self.inspector, "Asking again for the same lot")

        submit_approval_response(approval, approver, "APPROVED", comments="OK, finish after")
        lot.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")
        self.assertEqual(report.status, "PENDING", "no verdict: the plan wasn't met")
        self.assertIsNone(ri.receiving_execution(lot))

    def test_a_holder_approves_their_own_in_one_step(self):
        lot = self._lot()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/accept_incomplete/",
                                {"reason": "Customer hot order; QA signs for the risk"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["outcome"], "ACCEPTED")
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")
        self.assertEqual(self._report(lot).status, "PENDING")

    def test_rejected_request_leaves_the_lot_under_inspection(self):
        from Tracker.services.core.approval import submit_approval_response
        approver = User.objects.create_user(username="qa3", email="qa3@x.test", password="x",
                                            tenant=self.tenant)
        self._qa_group(approver)
        lot = self._lot()
        _, approval = ri.request_accept_incomplete(
            self._report(lot), self.inspector, "Want to use it before the sample is done")
        submit_approval_response(approval, approver, "REJECTED", comments="Finish the sample")
        lot.refresh_from_db()
        self.assertEqual(lot.status, "AWAITING_INSPECTION")

    def test_finishing_the_sample_cancels_the_waiting_request(self):
        lot = self._lot()
        report = self._report(lot)
        _, approval = ri.request_accept_incomplete(
            report, self.inspector, "Want to use it before the sample is done")
        report.status = "PASS"
        report.save(update_fields=["status"])
        ri.accept(report, self.qa)
        approval.refresh_from_db()
        self.assertEqual(approval.status, "CANCELLED")

    def test_the_record_says_accepted_unfinished_not_passed(self):
        from Tracker.reports.adapters.receiving_inspection_record import (
            build_receiving_inspection_record_context)
        lot = self._lot()
        ri.request_accept_incomplete(self._report(lot), self.qa,
                                     "Customer hot order; QA signs for the risk")
        lot.refresh_from_db()
        ctx = build_receiving_inspection_record_context(lot, self.tenant)
        self.assertEqual(ctx.verdict, "INCOMPLETE")
        row, = [e for e in ctx.events if e.what == "Accepted with the sample unfinished"]
        self.assertTrue(row.note.startswith("Customer hot order; QA signs for the risk (asked by"))
