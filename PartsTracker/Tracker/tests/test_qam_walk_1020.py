"""QA Manager walk findings (2026-10-20) that have no better home."""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    CalibrationRecord, Companies, EquipmentType, Equipments, MaterialLot, PartTypes,
    QualityReports, QuarantineDisposition, SamplingRule, SamplingRuleSet, Steps,
)
from Tracker.tests.base import TenantTestCase


class _Api(TenantTestCase):
    perms = ['full_tenant_access']

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, self.perms)
        self.authenticate_as(self.user_a, self.tenant_a)


class CalibrationFailedBucketTests(_Api):
    perms = ['view_calibrationrecord', 'full_tenant_access']

    def test_a_failed_gauge_is_its_own_bucket(self):
        """A gauge whose latest calibration failed sat in no bucket, so the dashboard's
        counts didn't add up."""
        gauge_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer",
                                                  requires_calibration=True)
        today = timezone.now().date()
        for name, result, due in (("MIC-1", "PASS", today + timedelta(days=200)),
                                  ("MIC-2", "FAIL", today + timedelta(days=200))):
            eq = Equipments.objects.create(tenant=self.tenant_a, name=name, equipment_type=gauge_type)
            CalibrationRecord.objects.create(tenant=self.tenant_a, equipment=eq, calibration_date=today,
                                             due_date=due, result=result)
        stats = self.client.get("/api/CalibrationRecords/stats/").json()
        self.assertEqual((stats["current_calibrations"], stats["failed"], stats["overdue"]), (1, 1, 0))


class SupplyingCompaniesTests(_Api):
    perms = ['view_companies', 'full_tenant_access']

    def test_only_companies_that_supply_something(self):
        """is_supplier defaults to true, so the scorecard listed customers and the
        tenant's own company as unqualified suppliers."""
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Seal")
        supplier = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes")
        customer = Companies.objects.create(tenant=self.tenant_a, name="Midwest Fleet")
        MaterialLot.objects.create(tenant=self.tenant_a, lot_number="L-1", supplier=supplier,
                                   material_type=pt, quantity=1, quantity_remaining=1,
                                   received_date=timezone.now().date(), unit_of_measure="EA")
        names = {c["name"] for c in self.client.get("/api/Companies/", {"supplying": "true"}).json()["results"]}
        self.assertIn(supplier.name, names)
        self.assertNotIn(customer.name, names)


class SamplingRuleEditTests(_Api):
    perms = ['view_samplingrule', 'change_samplingrule', 'full_tenant_access']

    def test_an_edit_is_one_audit_entry(self):
        """The walk saw two identical audit entries per rule edit."""
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        step = Steps.objects.create(tenant=self.tenant_a, name="Body Inspection", part_type=pt)
        rs = SamplingRuleSet.objects.create(tenant=self.tenant_a, part_type=pt, step=step, name="Standard")
        rule = SamplingRule.objects.create(tenant=self.tenant_a, ruleset=rs, rule_type="EVERY_NTH_PART",
                                           value=4, order=1)
        ct = ContentType.objects.get_for_model(SamplingRule)
        before = LogEntry.objects.filter(content_type=ct, object_pk=str(rule.pk)).count()
        resp = self.client.patch(f"/api/Sampling-rules/{rule.id}/", {"value": 2}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(LogEntry.objects.filter(content_type=ct, object_pk=str(rule.pk)).count(), before + 1)


class DispositionDescriptionTests(TenantTestCase):

    def test_the_description_names_every_report_once_captures_are_in(self):
        """A step's captures land after its report first goes FAIL, so the description
        written then said only the step; a joining report never made it in."""
        from Tracker.models import MeasurementDefinition, MeasurementResult, Parts
        from Tracker.services.qms.disposition import refresh_disposition_description
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        step = Steps.objects.create(tenant=self.tenant_a, name="Body Inspection", part_type=pt)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="B-1", part_type=pt, step=step)
        visual = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=step, status="FAIL",
                                               description="Burr on the seat")
        disp = QuarantineDisposition.objects.get(quality_reports=visual)
        bore = MeasurementDefinition.objects.create(tenant=self.tenant_a, label="Bore", type="NUMERIC",
                                                    unit="mm", nominal=4.0, upper_tol=0.005, lower_tol=0.005,
                                                    step=step)
        measured = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=step, status="PENDING")
        MeasurementResult.objects.create(tenant=self.tenant_a, report=measured, definition=bore,
                                         value_numeric=4.007)
        disp.quality_reports.add(measured)
        disp.description = "Failed Body Inspection"
        disp.save(update_fields=["description"])
        refresh_disposition_description(disp)
        disp.refresh_from_db()
        self.assertEqual(disp.description,
                         "Failed Body Inspection: Burr on the seat, Bore 4.007 mm (limits 3.995–4.005)")


class BenchFindingTests(TenantTestCase):

    def test_the_latest_applied_finding_without_its_stamp(self):
        """The R1 dialog showed the scrap consequence ("not recovered"), then the whole
        notes; what the customer decides on is the bench finding."""
        from types import SimpleNamespace
        from Tracker.services.reman.rebuild import _bench_note
        hc = SimpleNamespace(condition_notes=(
            "Normal tip wear at teardown.\n"
            "Finding applied (Sarah C., 2026-10-20 16:02): grade B → SCRAP. "
            "Hairline crack at the needle guide, found under magnification after cleaning."))
        self.assertEqual(_bench_note(hc),
                         "Hairline crack at the needle guide, found under magnification after cleaning.")
        self.assertEqual(_bench_note(SimpleNamespace(condition_notes="Normal tip wear")), "Normal tip wear")
