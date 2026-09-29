"""Small follow-up fixes (2026-09-29).

1. ExternalContact API is gated by model perms (was: any tenant member could write).
2. ExternalContact `unsubscribe_token` is issued when a contact is turned on.
3. Capable-to-promise quotes only against an APPROVED, current routing.
4. Shift: an is_active flip saves in place (API and import); a content edit versions.
5. The work-centre dropdown lists current, live versions only.
6. CalibrationRecord import catches a duplicate that has no certificate number.
"""
import datetime as dt

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from Tracker.tests.base import TenantContextMixin, TenantTestCase
from Tracker.tests.io_base import ImportExportTestCase
from Tracker.tests.test_planning_rccp import _RccpFixture


# =============================================================================
# 1. ExternalContact permissions
# =============================================================================

EXTERNAL_CONTACT_PERMS = ['view_externalcontact', 'add_externalcontact',
                          'change_externalcontact', 'delete_externalcontact']


class ExternalContactPresetTests(SimpleTestCase):
    def test_viewset_applies_model_permissions(self):
        from Tracker.permissions import TenantModelPermissions
        from Tracker.viewsets.notifications import ExternalContactViewSet
        self.assertIn(TenantModelPermissions, ExternalContactViewSet.permission_classes)

    def test_notification_managers_hold_every_contact_perm(self):
        from Tracker.presets import GROUP_PRESETS
        for role in ('tenant_admin', 'qa_manager', 'production_manager'):
            perms = set(GROUP_PRESETS[role]['permissions'])
            for p in EXTERNAL_CONTACT_PERMS:
                self.assertIn(p, perms, f"{role} must hold {p}")

    def test_line_roles_cannot_write_contacts(self):
        from Tracker.presets import GROUP_PRESETS
        for role in ('operator', 'qa_inspector', 'customer'):
            perms = GROUP_PRESETS[role]['permissions']
            self.assertNotIn('add_externalcontact', perms, role)
            self.assertNotIn('delete_externalcontact', perms, role)

    def test_staff_can_view_contacts_but_customers_cannot(self):
        """Staff open notification rules, so they must be able to read the recipient
        contacts on them (decided 2026-09-29); an external customer must not."""
        from Tracker.presets import GROUP_PRESETS
        for role in ('operator', 'qa_inspector'):
            self.assertIn('view_externalcontact', GROUP_PRESETS[role]['permissions'], role)
        self.assertNotIn('view_externalcontact', GROUP_PRESETS['customer']['permissions'])


class ExternalContactApiPermissionTests(TenantTestCase):
    URL = '/api/notifications/external-contacts/'

    def setUp(self):
        super().setUp()
        from Tracker.models import Companies
        self.customer = Companies.objects.create(tenant=self.tenant_a, name='Acme')

    def _post(self):
        return self.client.post(self.URL, {
            'customer': str(self.customer.id), 'name': 'Buyer',
            'email': 'buyer@acme.example', 'role': 'procurement',
        }, format='json')

    def test_a_member_without_the_perm_cannot_create(self):
        from Tracker.models import ExternalContact
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_companies'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self._post()
        self.assertEqual(r.status_code, 403, r.content[:500])
        self.assertFalse(ExternalContact.objects.filter(email='buyer@acme.example').exists())

    def test_a_member_with_the_perm_can_create(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      EXTERNAL_CONTACT_PERMS + ['view_companies'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self._post()
        self.assertEqual(r.status_code, 201, r.content[:500])


# =============================================================================
# 2. ExternalContact unsubscribe token
# =============================================================================

class ExternalContactTokenTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Companies, Tenant
        self.tenant = Tenant.objects.create(name='Tok', slug='tok-0929')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(tenant=self.tenant, name='Acme')

    def _create(self, **extra):
        from Tracker.serializers.notifications import ExternalContactSerializer
        ser = ExternalContactSerializer(data={
            'customer': self.customer.id, 'name': 'Buyer',
            'email': 'buyer@acme.example', **extra})
        self.assertTrue(ser.is_valid(), ser.errors)
        return ser.save(tenant=self.tenant)

    def _update(self, contact, **data):
        from Tracker.serializers.notifications import ExternalContactSerializer
        ser = ExternalContactSerializer(contact, data=data, partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)
        contact = ser.save()
        contact.refresh_from_db()
        return contact

    def test_a_contact_created_enabled_gets_a_token(self):
        self.assertTrue(self._create().unsubscribe_token)

    def test_a_contact_created_disabled_gets_none(self):
        self.assertEqual(self._create(enabled=False).unsubscribe_token, '')

    def test_re_enabling_rotates_the_token(self):
        contact = self._create()
        first = contact.unsubscribe_token
        contact = self._update(contact, enabled=False)
        self.assertEqual(contact.unsubscribe_token, first)  # turning off keeps it
        contact = self._update(contact, enabled=True)
        self.assertTrue(contact.unsubscribe_token)
        self.assertNotEqual(contact.unsubscribe_token, first)

    def test_an_edit_that_does_not_turn_it_on_keeps_the_token(self):
        contact = self._create()
        first = contact.unsubscribe_token
        contact = self._update(contact, name='Renamed', enabled=True)
        self.assertEqual(contact.unsubscribe_token, first)

    def test_the_token_is_not_exposed(self):
        from Tracker.serializers.notifications import ExternalContactSerializer
        self.assertNotIn('unsubscribe_token', ExternalContactSerializer().fields)


class ExternalContactImportTokenTests(ImportExportTestCase):
    endpoint = "notifications/external-contacts"
    tenant_slug = "io-extcontact-0929"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Companies, ExternalContact
        cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
        cls.off = ExternalContact.objects.create(
            tenant=cls.tenant, customer=cls.acme, name="Jane", email="jane@acme.example",
            enabled=False, unsubscribe_token="old-token")

    def test_an_import_that_re_enables_rotates_the_token(self):
        from Tracker.models import ExternalContact
        body = self.import_csv("customer,email,enabled\nAcme,jane@acme.example,true\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        c = ExternalContact.objects.get(pk=self.off.pk)
        self.assertTrue(c.enabled)
        self.assertTrue(c.unsubscribe_token)
        self.assertNotEqual(c.unsubscribe_token, "old-token")

    def test_an_imported_new_contact_gets_a_token(self):
        from Tracker.models import ExternalContact
        body = self.import_csv("customer,name,email\nAcme,Bob,bob@acme.example\n",
                               mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertTrue(ExternalContact.objects.get(email="bob@acme.example").unsubscribe_token)


# =============================================================================
# 3. Capable-to-promise resolves an approved routing
# =============================================================================

class CtpUsesApprovedProcessTests(_RccpFixture, TestCase):
    def _ctp(self, qty=5):
        from Tracker.services.planning import rccp
        return rccp.capable_to_promise(
            self.tenant, self.pt.id, qty, timezone.now().date() + dt.timedelta(days=20),
            months=6)

    def test_a_newer_draft_does_not_displace_the_approved_routing(self):
        """The newest process is an empty DRAFT. The old pick (newest, any status)
        quoted against it and answered "no routing steps"."""
        from Tracker.models import Processes, ProcessStatus
        Processes.objects.create(tenant=self.tenant, name="W draft", part_type=self.pt,
                                 status=ProcessStatus.DRAFT)
        r = self._ctp()
        self.assertTrue(r["feasible"], r)

    def test_only_a_draft_process_is_no_routing(self):
        from Tracker.models import ProcessStatus
        self.process.status = ProcessStatus.DRAFT
        self.process.save(update_fields=["status"])
        r = self._ctp()
        self.assertFalse(r["feasible"])
        self.assertIn("No approved process/routing", r["reason"])


# =============================================================================
# 4. Shift is_active flip does not version
# =============================================================================

class ShiftApiVersioningTests(ImportExportTestCase):
    endpoint = "Shifts"
    tenant_slug = "shift-0929"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Shift
        cls.shift = Shift.objects.create(
            tenant=cls.tenant, name="Day", code="DAY", start_time=dt.time(6, 0),
            end_time=dt.time(14, 0), days_of_week="0,1,2,3,4", is_active=True)

    def _patch(self, data):
        r = self.client.patch(f"/api/Shifts/{self.shift.id}/", data, format="json")
        self.assertEqual(r.status_code, 200, r.content[:1000])
        return r.json()

    def test_an_is_active_toggle_saves_in_place(self):
        from Tracker.models import Shift
        body = self._patch({"is_active": False})
        self.assertEqual(body["id"], str(self.shift.id))
        self.assertEqual(Shift.objects.filter(code="DAY").count(), 1)
        s = Shift.objects.get(pk=self.shift.pk)
        self.assertFalse(s.is_active)
        self.assertEqual(s.version, 1)

    def test_a_whole_form_toggle_saves_in_place(self):
        from Tracker.models import Shift
        self._patch({"name": "Day", "code": "DAY", "start_time": "06:00:00",
                     "end_time": "14:00:00", "days_of_week": "0,1,2,3,4",
                     "is_active": False})
        self.assertEqual(Shift.objects.filter(code="DAY").count(), 1)

    def test_a_content_edit_still_versions(self):
        from Tracker.models import Shift
        body = self._patch({"end_time": "15:00:00"})
        self.assertNotEqual(body["id"], str(self.shift.id))
        current = Shift.objects.get(code="DAY", is_current_version=True)
        self.assertEqual(current.version, 2)
        self.assertEqual(current.end_time, dt.time(15, 0))

    def test_an_unchanged_patch_makes_no_version(self):
        from Tracker.models import Shift
        self._patch({"end_time": "14:00:00"})
        self.assertEqual(Shift.objects.filter(code="DAY").count(), 1)

    def test_an_imported_is_active_flip_saves_in_place(self):
        from Tracker.models import Shift
        body = self.import_csv("code,is_active\nDAY,false\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(Shift.objects.filter(code="DAY").count(), 1)
        self.assertFalse(Shift.objects.get(pk=self.shift.pk).is_active)

    def test_the_importer_no_longer_forces_versioning(self):
        from Tracker.viewsets.mes_standard import ShiftViewSet
        self.assertFalse(getattr(ShiftViewSet.csv_import_serializer.Meta,
                                 'update_via_new_version', False))


# =============================================================================
# 5. Work-centre dropdown
# =============================================================================

class WorkCenterOptionsTests(ImportExportTestCase):
    endpoint = "WorkCenters-Options"
    tenant_slug = "wc-options-0929"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import WorkCenter
        cls.old = WorkCenter.objects.create(tenant=cls.tenant, name="Cell A", code="A")
        cls.current = cls.old.create_new_version(name="Cell A (rev 2)")
        cls.gone = WorkCenter.objects.create(tenant=cls.tenant, name="Cell Z", code="Z",
                                             archived=True)

    def test_only_current_live_versions_are_offered(self):
        r = self.client.get("/api/WorkCenters-Options/")
        self.assertEqual(r.status_code, 200, r.content[:1000])
        body = r.json()
        rows = body["results"] if isinstance(body, dict) else body
        ids = {row["id"] for row in rows}
        self.assertEqual(ids, {str(self.current.id)})


# =============================================================================
# 6. Calibration duplicate with no certificate
# =============================================================================

class CalibrationUncertifiedDuplicateTests(ImportExportTestCase):
    endpoint = "CalibrationRecords"
    tenant_slug = "io-calibration-0929"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import CalibrationRecord, EquipmentType, Equipments
        gauge = EquipmentType.objects.create(tenant=cls.tenant, name="Micrometer")
        cls.mic = Equipments.objects.create(tenant=cls.tenant, name="Mic 0-1in",
                                            serial_number="SN-200", equipment_type=gauge)
        CalibrationRecord.objects.create(
            tenant=cls.tenant, equipment=cls.mic, calibration_date=dt.date(2026, 1, 15),
            due_date=dt.date(2027, 1, 15), result="PASS", calibration_type="SCHEDULED",
            certificate_number="")

    def test_an_uncertified_repeat_is_refused_not_a_second_record(self):
        from Tracker.models import CalibrationRecord
        # The date typed the way a person types it: the local find_existing reads it.
        body = self.import_csv("equipment,calibration_date,due_date\n"
                               "SN-200,1/15/2026,2027-01-15\n", mode="create")
        self.assert_row_errors(body, mentions="already exists")
        self.assertEqual(CalibrationRecord.objects.count(), 1)

    def test_an_uncertified_record_on_another_date_is_added(self):
        from Tracker.models import CalibrationRecord
        body = self.import_csv("equipment,calibration_date,due_date,result\n"
                               "SN-200,2026-07-15,2027-07-15,PASS\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(CalibrationRecord.objects.count(), 2)

    def test_a_certified_record_does_not_match_the_uncertified_one(self):
        from Tracker.models import CalibrationRecord
        body = self.import_csv("equipment,calibration_date,due_date,result,certificate_number\n"
                               "SN-200,2026-01-15,2027-01-15,PASS,C-9\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(CalibrationRecord.objects.count(), 2)
