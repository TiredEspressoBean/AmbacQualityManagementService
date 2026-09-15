"""A voided completion no longer satisfies its substep for the sequencing gate.

`Steps.sequencing_mode='sequential'` means a substep can't be completed until
the earlier required ones are done. `_enforce_sequencing` read every
SubstepCompletion on the execution as "done" regardless of `is_voided`, so
after QA voided substep #1 the operator could still submit #2 — the retracted
row still satisfied the order check.

That matters because the *advancement* gate does filter voided rows. The part
would pass the sequencing gate, accumulate more work, and then block at
advancement instead: one step downstream of the cause, reading as an unrelated
block. Both sibling gates (`advancement_gate`, `batch_lifecycle`) already
filtered; this one is the outlier that didn't.
"""
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import (
    BatchExecution, Parts, PartTypes, Processes, ProcessStep, StepExecution,
    Steps, Substep, SubstepCompletion, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.dwi.operator_capture import submit_substep
from Tracker.tests.base import TenantContextMixin, VectorTestCase


def _attestation():
    return [{"node_id": str(uuid4()), "kind": "attestation", "confirm": True}]


class VoidBlocksSequencingTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Void Seq", slug="void-seq", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-seq", email="s@s.test", password="x", tenant=self.tenant,
        )
        self.qa = User.objects.create_user(
            username="qa-seq", email="q@q.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-SEQ", part_type=self.part_type,
        )
        # Sequential is the default, but state it — the whole test is about
        # this mode, and a default that drifts would silently void the test.
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Assemble",
            step_type="TASK", sequencing_mode="sequential",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.first = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Torque bolts",
            is_optional=False,
        )
        self.second = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=1, title="Verify torque",
            is_optional=False,
        )
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-SEQ-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
            process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-SEQ-1", part_type=self.part_type,
            work_order=self.wo, step=self.step,
        )
        self.se = StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step,
            visit_number=1, status="IN_PROGRESS",
        )

    def test_second_substep_blocked_while_first_is_open(self):
        """Baseline: without the first completion, the gate already blocks.

        Here so a later failure can be read as "the void wasn't respected"
        rather than "the gate never worked".
        """
        with self.assertRaises(ValidationError):
            submit_substep(
                substep=self.second, step_execution=self.se, user=self.user,
                captures=_attestation(),
            )

    def test_completing_first_unblocks_second(self):
        submit_substep(
            substep=self.first, step_execution=self.se, user=self.user,
            captures=_attestation(),
        )
        result = submit_substep(
            substep=self.second, step_execution=self.se, user=self.user,
            captures=_attestation(),
        )
        self.assertIsNotNone(result.completion_id)

    def test_voiding_the_first_re_blocks_the_second(self):
        """The regression.

        QA voids #1 after it was signed. #2 must block again — otherwise the
        operator keeps working on a part whose earlier step no longer holds,
        and only finds out at the advancement gate.
        """
        submit_substep(
            substep=self.first, step_execution=self.se, user=self.user,
            captures=_attestation(),
        )
        completion = SubstepCompletion.objects.get(
            step_execution=self.se, substep=self.first,
        )
        completion.void(self.qa, "gauge was out of calibration")

        with self.assertRaises(ValidationError):
            submit_substep(
                substep=self.second, step_execution=self.se, user=self.user,
                captures=_attestation(),
            )

    def test_voiding_a_batch_completion_re_blocks_the_next_batch_substep(self):
        """Same fix, batch branch — it had the identical omission.

        Worth its own case: the two branches read different columns
        (`batch_execution` vs `step_execution`), so fixing one proves nothing
        about the other.
        """
        first_batch = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=2, title="Confirm cycle",
            scope="batch", is_optional=False,
        )
        second_batch = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=3, title="Record bath pH",
            scope="batch", is_optional=False,
        )
        batch = BatchExecution.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step,
            started_by=self.user,
        )
        batch.parts.set([self.part])

        submit_substep(
            substep=first_batch, batch_execution=batch, user=self.user,
            captures=_attestation(),
        )
        # Unblocked while the first batch completion stands.
        submit_substep(
            substep=second_batch, batch_execution=batch, user=self.user,
            captures=_attestation(),
        )

        SubstepCompletion.objects.get(
            batch_execution=batch, substep=first_batch,
        ).void(self.qa, "cycle chart unreadable")
        SubstepCompletion.objects.filter(
            batch_execution=batch, substep=second_batch,
        ).delete()

        with self.assertRaises(ValidationError):
            submit_substep(
                substep=second_batch, batch_execution=batch, user=self.user,
                captures=_attestation(),
            )
