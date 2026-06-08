"""
Tests for bulk-instantiation actions across MES (parts) and reman (cores).

Covers:
- WorkOrderViewSet.bulk_add_parts (WS1)
- CoreViewSet.bulk_create (WS2)
- CoreViewSet.start_teardown_batch (WS3)
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from Tracker.models import (
    Companies,
    Core,
    PartsStatus,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)

User = get_user_model()


class BulkActionsBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Bulk Shop", slug="bulk-shop")
        cls._class_cv_token = set_current_tenant_id(cls.tenant.id)

        cls.user = User.objects.create_user(
            username="bulk_user", email="bulk@test.com",
            password="testpass", tenant=cls.tenant, is_staff=True,
        )
        cls.user.is_superuser = True
        cls.user.save(update_fields=['is_superuser'])

        cls.customer = Companies.objects.create(name="Bulk Customer", tenant=cls.tenant)

        cls.injector_type = PartTypes.objects.create(
            name="Fuel Injector", ID_prefix="INJ", tenant=cls.tenant,
        )
        cls.other_type = PartTypes.objects.create(
            name="Pump", ID_prefix="PMP", tenant=cls.tenant,
        )

        cls.process = Processes.objects.create(
            name="Injector Build",
            part_type=cls.injector_type,
            tenant=cls.tenant,
            status=ProcessStatus.APPROVED,
        )
        cls.disassembly_process = Processes.objects.create(
            name="Injector Teardown",
            part_type=cls.injector_type,
            tenant=cls.tenant,
            status=ProcessStatus.APPROVED,
            is_remanufactured=True,
            is_disassembly=True,
        )

        cls.step1 = Steps.objects.create(
            name="Step 1", part_type=cls.injector_type, tenant=cls.tenant,
        )
        cls.step2 = Steps.objects.create(
            name="Step 2", part_type=cls.injector_type, tenant=cls.tenant,
        )
        ProcessStep.objects.create(process=cls.process, step=cls.step1, order=1)
        ProcessStep.objects.create(process=cls.process, step=cls.step2, order=2)

        cls.teardown_step = Steps.objects.create(
            name="Teardown", part_type=cls.injector_type, tenant=cls.tenant,
        )
        ProcessStep.objects.create(
            process=cls.disassembly_process, step=cls.teardown_step, order=1,
        )

        cls.work_order = WorkOrder.objects.create(
            tenant=cls.tenant,
            ERP_id="WO-BULK-001",
            workorder_status=WorkOrderStatus.PENDING,
            quantity=5,
            process=cls.process,
        )

    @classmethod
    def tearDownClass(cls):
        token = getattr(cls, '_class_cv_token', None)
        if token is not None:
            reset_current_tenant(token)
            cls._class_cv_token = None
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._test_cv_token = set_current_tenant_id(self.tenant.id)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))

    def tearDown(self):
        token = getattr(self, '_test_cv_token', None)
        if token is not None:
            reset_current_tenant(token)
            self._test_cv_token = None
        super().tearDown()


class WorkOrderBulkAddPartsTests(BulkActionsBaseTestCase):
    """WS1: POST /api/WorkOrders/{id}/bulk_add_parts/"""

    def url(self):
        return f"/api/WorkOrders/{self.work_order.id}/bulk_add_parts/"

    def test_creates_n_parts_attached_to_wo(self):
        response = self.client.post(self.url(), {
            "part_type": str(self.injector_type.id),
            "step": str(self.step1.id),
            "quantity": 3,
        }, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['count'], 3)
        self.assertEqual(len(body['created_part_ids']), 3)
        self.assertEqual(self.work_order.parts.count(), 3)

    def test_erp_id_start_offsets_sequence(self):
        response = self.client.post(self.url(), {
            "part_type": str(self.injector_type.id),
            "step": str(self.step1.id),
            "quantity": 2,
            "erp_id_start": 10,
        }, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        erp_ids = sorted(self.work_order.parts.values_list('ERP_id', flat=True))
        self.assertEqual(erp_ids, [
            f"{self.work_order.ERP_id}-INJ0010",
            f"{self.work_order.ERP_id}-INJ0011",
        ])

    def test_validates_part_type_matches_process_part_type(self):
        response = self.client.post(self.url(), {
            "part_type": str(self.other_type.id),
            "step": str(self.step1.id),
            "quantity": 1,
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn('part_type', response.json()['detail'])
        self.assertEqual(self.work_order.parts.count(), 0)

    def test_missing_fields_returns_400(self):
        response = self.client.post(self.url(), {
            "quantity": 3,
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_step_id_returns_400(self):
        response = self.client.post(self.url(), {
            "part_type": str(self.injector_type.id),
            "step": "00000000-0000-0000-0000-000000000000",
            "quantity": 1,
        }, format="json")
        self.assertEqual(response.status_code, 400)


class CoreBulkCreateTests(BulkActionsBaseTestCase):
    """WS2: POST /api/Cores/bulk_create/"""

    def url(self):
        return "/api/Cores/bulk_create/"

    def _row(self, core_number, **overrides):
        row = {
            "core_number": core_number,
            "core_type": str(self.injector_type.id),
            "received_date": date.today().isoformat(),
            "source_type": "CUSTOMER_RETURN",
            "condition_grade": "B",
        }
        row.update(overrides)
        return row

    def test_bulk_create_n_cores(self):
        response = self.client.post(self.url(), {
            "cores": [
                self._row("BULK-001"),
                self._row("BULK-002"),
                self._row("BULK-003"),
            ],
        }, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['count'], 3)
        self.assertEqual(len(body['created_core_ids']), 3)
        self.assertEqual(Core.objects.count(), 3)
        for core in Core.objects.all():
            self.assertEqual(core.received_by_id, self.user.id)
            self.assertEqual(core.status, 'RECEIVED')

    def test_all_or_nothing_on_validation_error(self):
        response = self.client.post(self.url(), {
            "cores": [
                self._row("ATOMIC-001"),
                self._row("ATOMIC-002", core_type="not-a-uuid"),
                self._row("ATOMIC-003"),
            ],
        }, format="json")

        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertIn('errors', body)
        # At least the bad row should be flagged with its index.
        bad = [e for e in body['errors'] if e['index'] == 1]
        self.assertTrue(bad)
        self.assertEqual(Core.objects.count(), 0)

    def test_all_or_nothing_on_duplicate_core_number(self):
        Core.objects.create(
            tenant=self.tenant, core_number="EXISTS",
            core_type=self.injector_type, received_date=date.today(),
            received_by=self.user, condition_grade='A',
        )
        response = self.client.post(self.url(), {
            "cores": [
                self._row("NEW-001"),
                self._row("EXISTS"),
            ],
        }, format="json")
        # Either 400 (validation) or 500 — but no new rows committed.
        self.assertNotEqual(response.status_code, 201)
        self.assertEqual(Core.objects.count(), 1)

    def test_empty_cores_returns_400(self):
        response = self.client.post(self.url(), {"cores": []}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_optional_fields_pass_through(self):
        response = self.client.post(self.url(), {
            "cores": [self._row(
                "OPT-001",
                serial_number="SN-123",
                source_reference="RMA-9",
                condition_notes="ok",
                core_credit_value="42.00",
                customer=str(self.customer.id),
            )],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        core = Core.objects.get(core_number="OPT-001")
        self.assertEqual(core.serial_number, "SN-123")
        self.assertEqual(core.source_reference, "RMA-9")
        self.assertEqual(core.core_credit_value, Decimal("42.00"))
        self.assertEqual(core.customer_id, self.customer.id)


class CoreStartTeardownBatchTests(BulkActionsBaseTestCase):
    """WS3: POST /api/Cores/start_teardown_batch/"""

    def url(self):
        return "/api/Cores/start_teardown_batch/"

    def _make_received_core(self, number, core_type=None):
        return Core.objects.create(
            tenant=self.tenant,
            core_number=number,
            core_type=core_type or self.injector_type,
            received_date=date.today(),
            received_by=self.user,
            condition_grade='A',
        )

    def test_creates_one_wo_and_transitions_cores(self):
        cores = [
            self._make_received_core("TD-001"),
            self._make_received_core("TD-002"),
            self._make_received_core("TD-003"),
        ]

        response = self.client.post(self.url(), {
            "core_ids": [str(c.id) for c in cores],
        }, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertIn('work_order_id', body)
        self.assertEqual(len(body['transitioned_core_ids']), 3)

        wo = WorkOrder.objects.get(id=body['work_order_id'])
        for core in cores:
            core.refresh_from_db()
            self.assertEqual(core.status, 'IN_DISASSEMBLY')
            self.assertEqual(core.work_order_id, wo.id)
            self.assertIsNotNone(core.disassembly_started_at)

    def test_rejects_mismatched_core_types(self):
        c1 = self._make_received_core("MIX-001", core_type=self.injector_type)
        c2 = self._make_received_core("MIX-002", core_type=self.other_type)

        response = self.client.post(self.url(), {
            "core_ids": [str(c1.id), str(c2.id)],
        }, format="json")

        self.assertEqual(response.status_code, 400)
        c1.refresh_from_db()
        c2.refresh_from_db()
        self.assertEqual(c1.status, 'RECEIVED')
        self.assertEqual(c2.status, 'RECEIVED')

    def test_rejects_cores_not_in_received(self):
        c1 = self._make_received_core("BAD-001")
        c2 = self._make_received_core("BAD-002")
        c2.status = 'IN_DISASSEMBLY'
        c2.save(update_fields=['status'])

        response = self.client.post(self.url(), {
            "core_ids": [str(c1.id), str(c2.id)],
        }, format="json")

        self.assertEqual(response.status_code, 400)
        c1.refresh_from_db()
        self.assertEqual(c1.status, 'RECEIVED')

    def test_rejects_cores_already_linked_to_wo(self):
        c1 = self._make_received_core("WO-LINKED-001")
        c1.work_order = self.work_order
        c1.save(update_fields=['work_order'])

        response = self.client.post(self.url(), {
            "core_ids": [str(c1.id)],
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_explicit_process_id_used_when_provided(self):
        cores = [self._make_received_core("EXP-001")]
        response = self.client.post(self.url(), {
            "core_ids": [str(c.id) for c in cores],
            "process_id": str(self.disassembly_process.id),
        }, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        wo = WorkOrder.objects.get(id=response.json()['work_order_id'])
        self.assertEqual(wo.process_id, self.disassembly_process.id)