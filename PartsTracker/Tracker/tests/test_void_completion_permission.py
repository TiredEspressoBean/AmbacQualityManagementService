"""Voiding a substep completion is gated on `void_substepcompletion`.

Voiding retracts a record of work someone else signed. The advancement gate
then ignores the voided row, so the part blocks until the work is redone, and
on an unsplit lot that holds the whole lot. It is a quality-record judgement,
not a production override.

This is regression cover for a gate that had been absent. `void` is a POST, so
under the CRUD default it required `add_substepcompletion` — a permission every
role holds, including the Operator whose completion is being invalidated.
`change_substepcompletion` is no narrower. The fix is a marker perm plus
`crud_exempt_actions`, and the exemption is the fragile half: drop it and the
`add_` gate applies again, silently re-widening the action to everyone. Hence
the negative case below, which is the one that would catch that.
"""
from Tracker.models import (
    Parts, PartTypes, Processes, ProcessStep, StepExecution, Steps,
    Substep, SubstepCompletion, WorkOrder, WorkOrderStatus,
)
from Tracker.presets import GROUP_PRESETS
from Tracker.tests.base import TenantTestCase

# What every floor role holds for this model. These are the permissions that
# used to be enough to void.
#
# `full_tenant_access` is in here so both cases reach the permission gate at
# all. Without it `SecureQuerySet.for_user` narrows to records related to the
# user's own orders, `get_object()` 404s, and the test would pass for the wrong
# reason — reporting "denied" when the row was merely invisible. Every preset
# that can void holds it, so this matches production rather than working
# around it.
CRUD_ONLY = [
    'view_substepcompletion',
    'add_substepcompletion',
    'change_substepcompletion',
    'full_tenant_access',
]


class VoidCompletionPermissionTests(TenantTestCase):
    def setUp(self):
        # TenantTestCase.setUp already points the ContextVar at tenant_a and
        # hands us a fresh APIClient, so there is nothing to set up here.
        super().setUp()

        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Widget")
        process = Processes.objects.create(
            tenant=self.tenant_a, name="P-VOID", part_type=pt,
        )
        step = Steps.objects.create(
            tenant=self.tenant_a, part_type=pt, name="Op-VOID", step_type="TASK",
        )
        ProcessStep.objects.create(process=process, step=step, order=1)
        wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-VOID-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
            process=process,
        )
        part = Parts.objects.create(
            tenant=self.tenant_a, ERP_id="P-VOID-1", part_type=pt,
            work_order=wo, step=step,
        )
        se = StepExecution.objects.create(
            tenant=self.tenant_a, part=part, step=step,
            visit_number=1, status="IN_PROGRESS",
        )
        substep = Substep.objects.create(
            tenant=self.tenant_a, step=step, title="Visual", order=1,
        )
        # user_a's own completion — the row QA would retract.
        self.completion = SubstepCompletion.objects.create(
            tenant=self.tenant_a, step_execution=se, substep=substep,
            completed_by=self.user_a,
        )

    def _void(self, user, reason="gauge was out of calibration"):
        self.authenticate_as(user, self.tenant_a)
        return self.client.post(
            f'/api/SubstepCompletions/{self.completion.id}/void/',
            {'reason': reason},
            format='json',
        )

    def test_holder_of_marker_perm_may_void(self):
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, CRUD_ONLY + ['void_substepcompletion'],
        )
        res = self._void(self.user_a)
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res))

        self.completion.refresh_from_db()
        self.assertTrue(self.completion.is_voided)
        # The reason is the audit record for why the work was retracted, so an
        # accepted void must persist it.
        self.assertIn("calibration", self.completion.void_reason)

    def test_crud_permissions_alone_are_not_enough(self):
        """The regression that matters.

        A user holding view/add/change on the model — what every floor role
        has — must not be able to void. If `crud_exempt_actions` ever stops
        covering `void`, the POST falls back to the `add_` gate and this
        starts passing a 200.
        """
        self.grant_tenant_permissions(self.user_a, self.tenant_a, CRUD_ONLY)
        res = self._void(self.user_a)
        self.assertEqual(res.status_code, 403, getattr(res, 'data', res))

        self.completion.refresh_from_db()
        self.assertFalse(self.completion.is_voided)


class VoidPermissionPresetTests(TenantTestCase):
    """Who holds `void_substepcompletion`, asserted against the presets.

    The gate above proves the permission is *enforced*; this proves it is
    *granted to the right roles*. Both halves are needed — a correctly enforced
    permission that nobody holds is just as broken as an unenforced one, and
    the failure looks like "the button never appears" rather than an error.
    """

    # Voiding retracts a quality record, so it is deliberately withheld from
    # the production chain of command: Shift Lead and Production Manager
    # supervise the work, they don't adjudicate it.
    EXPECTED_HOLDERS = {'qa_inspector', 'qa_manager', 'tenant_admin'}

    def _holders(self):
        return {
            key for key, preset in GROUP_PRESETS.items()
            if 'void_substepcompletion' in preset['permissions']
        }

    def test_exactly_the_intended_roles_hold_it(self):
        self.assertEqual(self._holders(), self.EXPECTED_HOLDERS)

    def test_floor_roles_do_not_hold_it(self):
        """Spelled out separately because this is the direction that matters.

        Widening is the silent failure: an Operator who can void their own
        rejected work erases the evidence, and nothing errors.
        """
        holders = self._holders()
        for role in ('operator', 'shift_lead', 'production_manager'):
            self.assertNotIn(role, holders, f"{role} must not be able to void")
