"""Z1.4 severity-switching engine tests (Normal ↔ Tightened ↔ Reduced + discontinue).

Drives the switching state machine directly by decided-lot outcomes — independent
of the exact Table II-B/II-C cell values (those are exercised separately). Each
lot's outcome is controlled via the report's snapshot Ac/Re + defectives.
"""
import datetime
from decimal import Decimal

from Tracker.tests.base import TenantTestCase
from Tracker.models import (
    Companies, PartTypes, Steps, MaterialLot, QualityReports,
    SamplingRuleSet, SamplingSeverityState,
)
from Tracker.services.qms import severity_switching as sw


class SeveritySwitchingTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes Diesel", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Gear")
        self.step = Steps.objects.create(
            tenant=self.tenant_a, name="Receiving Inspection", part_type=self.part_type, step_type="RECEIVING")
        self.ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, step=self.step, supplier=self.supplier,
            name="Receiving Z1.4", active=True, aql=Decimal("1.0"),
            inspection_level="II", severity="NORMAL", strategy="Z14")
        self._seq = 0

    def _decide(self, status, *, ac, re, defectives):
        """Create a decided receiving report for the (step, supplier) and run the engine."""
        self._seq += 1
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number=f"LOT-{self._seq:03d}",
            received_date=datetime.date(2026, 1, 1), received_by=self.user_a,
            quantity=Decimal("500"), quantity_remaining=Decimal("500"),
            unit_of_measure="EA", status="ACCEPTED", material_type=self.part_type, supplier=self.supplier)
        report = QualityReports.objects.create(
            tenant=self.tenant_a, material_lot=lot, step=self.step, status=status,
            accept_number=ac, reject_number=re, defectives_found=defectives, detected_by=self.user_a)
        sw.update_after_lot(report)
        return report

    def _accept(self):
        return self._decide("PASS", ac=2, re=3, defectives=0)

    def _reject(self):
        return self._decide("FAIL", ac=2, re=3, defectives=3)

    def _reduced_gap(self):
        # Reduced plan: Re > Ac + 1; defectives land in the accept-but-revert gap.
        return self._decide("PASS", ac=1, re=4, defectives=2)

    def _severity(self):
        st = SamplingSeverityState.objects.filter(step=self.step, supplier=self.supplier).first()
        return st.severity if st else "NORMAL"

    # --- transitions --------------------------------------------------------

    def test_normal_to_tightened_two_rejects_in_five(self):
        self._accept(); self._reject(); self._accept(); self._reject()  # 2 rejects within 4
        self.assertEqual(self._severity(), "TIGHTENED")

    def test_normal_to_reduced_ten_consecutive_accepts(self):
        for _ in range(10):
            self._accept()
        self.assertEqual(self._severity(), "REDUCED")

    def test_tightened_to_normal_five_consecutive_accepts(self):
        self._reject(); self._reject()                      # → TIGHTENED
        self.assertEqual(self._severity(), "TIGHTENED")
        for _ in range(5):
            self._accept()
        self.assertEqual(self._severity(), "NORMAL")

    def test_reduced_reverts_to_normal_on_reject(self):
        for _ in range(10):
            self._accept()                                  # → REDUCED
        self.assertEqual(self._severity(), "REDUCED")
        self._reject()
        self.assertEqual(self._severity(), "NORMAL")

    def test_reduced_reverts_to_normal_on_gap(self):
        for _ in range(10):
            self._accept()                                  # → REDUCED
        self.assertEqual(self._severity(), "REDUCED")
        self._reduced_gap()                                 # accepted, but reduced discontinues
        self.assertEqual(self._severity(), "NORMAL")

    def test_discontinue_latches_and_emits(self):
        from Tracker.services.core.notifications.emit import notification_event
        seen = []
        rcv = lambda sender, **kw: seen.append(kw.get("event_code"))
        notification_event.connect(rcv, weak=False)
        try:
            self._reject(); self._reject()                  # → TIGHTENED (regime reset)
            # 5 lots on tightened without 5 consecutive accepts → discontinue.
            self._accept(); self._accept(); self._reject(); self._accept(); self._accept()
        finally:
            notification_event.disconnect(rcv)
        st = SamplingSeverityState.objects.get(step=self.step, supplier=self.supplier)
        self.assertTrue(st.discontinued)
        self.assertIn("supplier.inspection_discontinued", seen)

    def test_effective_severity_reflects_state(self):
        self._reject(); self._reject()                      # → TIGHTENED
        self.assertEqual(sw.effective_severity(self.step, self.supplier, self.ruleset), "TIGHTENED")

    def test_non_z14_is_noop(self):
        self.ruleset.strategy = "C0"
        self.ruleset.save(update_fields=["strategy"])
        self._reject(); self._reject()
        self.assertFalse(SamplingSeverityState.objects.filter(step=self.step, supplier=self.supplier).exists())

    # --- display status (switching_status) ----------------------------------

    def test_switching_status_tightened_countdown(self):
        self._reject(); self._reject()                      # → TIGHTENED
        self._accept(); self._accept()                      # 2 of the 5 needed
        st = SamplingSeverityState.objects.get(step=self.step, supplier=self.supplier)
        status = sw.switching_status(st)
        self.assertEqual(status["next_severity_on_accepts"], "NORMAL")
        self.assertEqual(status["accepts_needed"], 3)

    def test_switching_status_normal_counts_toward_reduced(self):
        for _ in range(4):
            self._accept()
        st = SamplingSeverityState.objects.get(step=self.step, supplier=self.supplier)
        status = sw.switching_status(st)
        self.assertEqual(status["next_severity_on_accepts"], "REDUCED")
        self.assertEqual(status["accepts_needed"], 6)
        self.assertEqual(status["rejects_in_window"], 0)

    def test_switching_status_reduced_has_no_accept_countdown(self):
        for _ in range(10):
            self._accept()                                  # → REDUCED
        st = SamplingSeverityState.objects.get(step=self.step, supplier=self.supplier)
        status = sw.switching_status(st)
        self.assertIsNone(status["accepts_needed"])
        self.assertEqual(status["next_severity_on_accepts"], "NORMAL")


class SeverityStateApiTests(TenantTestCase):
    """Read-only exposure: the badge data the inspector inbox renders."""

    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme Machining", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        self.step = Steps.objects.create(
            tenant=self.tenant_a, name="Receiving Inspection", part_type=self.part_type, step_type="RECEIVING")
        self.state = SamplingSeverityState.objects.create(
            tenant=self.tenant_a, step=self.step, supplier=self.supplier,
            severity="TIGHTENED", consecutive_accepts=2,
            recent_outcomes=["R", "A", "R", "A", "A"],
        )

    def _client(self):
        from rest_framework.test import APIClient
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ['view_samplingseveritystate', 'full_tenant_access'],
        )
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        return client

    def test_list_carries_derived_switching_fields(self):
        client = self._client()
        response = client.get(f'/api/SamplingSeverityStates/?supplier={self.supplier.id}')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        rows = body.get('results', body)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['severity'], 'TIGHTENED')
        self.assertEqual(row['supplier_name'], 'Acme Machining')
        self.assertEqual(row['rejects_in_window'], 2)
        self.assertEqual(row['next_severity_on_accepts'], 'NORMAL')
        self.assertEqual(row['accepts_needed'], 3)

    def test_endpoint_is_read_only(self):
        client = self._client()
        response = client.post('/api/SamplingSeverityStates/', {})
        # 405 from ReadOnlyModelViewSet routing; the permission layer may 403
        # first (no add_samplingseveritystate) — both prove not-writable.
        self.assertIn(response.status_code, (403, 405))
