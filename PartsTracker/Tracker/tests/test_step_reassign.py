"""Supervisor take-over and hand-off of a step in progress (2026-11-03): the step keeps
its status and draft, the record says who moved it and why, and the training gate still
applies to whoever ends up holding it."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from Tracker.models import (
    Parts, PartTypes, Processes, StepExecution, Steps, Substep, Tenant, TenantGroup,
    TrainingRequirement, TrainingType, UserRole, WorkOrder, WorkOrderStatus,
)
from Tracker.services.dwi.operator_capture import save_capture_draft
from Tracker.services.mes.lifecycle import NotQualified, reassign_execution
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class StepReassignTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Hand", slug="step-reassign", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        mk = lambda name: User.objects.create_user(  # noqa: E731
            username=name, email=f"{name}@r.test", password="x", tenant=self.tenant)
        self.lead, self.op, self.op2 = mk("lead"), mk("op"), mk("op2")
        self._grant(self.lead, "reassign_stepexecution", "override_training_gate",
                    "view_stepexecution", "full_tenant_access")
        self._grant(self.op, "view_stepexecution", "add_substepcompletion", "full_tenant_access")
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        process = Processes.objects.create(tenant=self.tenant, name="P", part_type=pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Lap", step_type="TASK")
        self.substep = Substep.objects.create(tenant=self.tenant, step=self.step, order=0, title="A")
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-R", process=process,
                                      workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1)
        part = Parts.objects.create(tenant=self.tenant, ERP_id="P-R", part_type=pt,
                                    work_order=wo, step=self.step)
        self.ex = StepExecution.objects.create(
            tenant=self.tenant, part=part, step=self.step, assigned_to=self.op,
            status="IN_PROGRESS", started_at=timezone.now(),
            capture_draft={str(self.substep.id): {"n": "15.2"}},
            training_authorization={"authorized": True, "missing": []})

    def _grant(self, user, *codenames):
        grp = TenantGroup.objects.create(tenant=self.tenant, name=f"g-{user.username}", is_custom=True)
        grp.permissions.add(*Permission.objects.filter(codename__in=codenames))
        UserRole.objects.create(user=user, group=grp)
        user.clear_permission_cache(self.tenant)

    def test_a_lead_takes_over_and_the_draft_and_status_carry_on(self):
        reassign_execution(self.ex, by=self.lead, to=self.lead, reason="Op went home sick")
        self.ex.refresh_from_db()
        self.assertEqual((self.ex.assigned_to_id, self.ex.status), (self.lead.id, "IN_PROGRESS"))
        self.assertEqual(self.ex.capture_draft[str(self.substep.id)], {"n": "15.2"})
        hand = self.ex.training_authorization["reassignment"]
        self.assertEqual((hand["from"], hand["to"], hand["authorized_by"], hand["reason"]),
                         (self.op.id, self.lead.id, self.lead.id, "Op went home sick"))
        self.assertEqual(self.ex.training_authorization["previous"], {"authorized": True, "missing": []})
        # The previous holder's open tab can no longer save over it.
        with self.assertRaises(PermissionDenied):
            save_capture_draft(self.ex, self.substep, {"n": "9"}, by=self.op)

    def test_a_hand_off_needs_a_reason_and_an_open_step(self):
        with self.assertRaises(ValidationError):
            reassign_execution(self.ex, by=self.lead, to=self.op2, reason=" ")
        with self.assertRaises(ValidationError):
            reassign_execution(self.ex, by=self.lead, to=self.op, reason="already theirs")
        self.ex.status = "COMPLETED"
        self.ex.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            reassign_execution(self.ex, by=self.lead, to=self.op2, reason="done already")

    def test_training_still_applies_to_whoever_holds_it(self):
        tt = TrainingType.objects.create(tenant=self.tenant, name="Lapping")
        TrainingRequirement.objects.create(tenant=self.tenant, training_type=tt, step=self.step)
        # The untrained lead can't authorize their own override.
        with self.assertRaises(NotQualified):
            reassign_execution(self.ex, by=self.lead, to=self.lead, reason="cover")
        # Handing on to an untrained operator, the lead authorizes it — on the record.
        reassign_execution(self.ex, by=self.lead, to=self.op2, reason="cover")
        self.ex.refresh_from_db()
        self.assertEqual(self.ex.training_authorization["override"]["authorized_by"], self.lead.id)

    def test_the_endpoint_is_the_supervisors_and_everyone_is_too(self):
        def client(user):
            c = APIClient()
            c.force_authenticate(user=user)
            c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
            return c
        url = f"/api/StepExecutions/{self.ex.id}/reassign/"
        r = client(self.op).post(url, {"to": self.op.id, "reason": "mine now"}, format="json")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(client(self.op).get("/api/StepExecutions/in-flight/", {"everyone": "1"}).status_code, 403)

        r = client(self.lead).post(url, {"to": self.op2.id, "reason": "Op on break all day"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = client(self.lead).get("/api/StepExecutions/in-flight/", {"everyone": "1"})
        self.assertEqual([row["holder_id"] for row in r.json()], [self.op2.id])
