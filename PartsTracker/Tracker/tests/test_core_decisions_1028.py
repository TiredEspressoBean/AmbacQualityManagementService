"""A remanufactured unit's decisions are the lead / planner tier (user decisions
2026-10-28, B4 and B5). They rode change_core / complete_disassembly in the shared
floor tier, so an operator could send a unit for authorisation, release it to its exit
or close its teardown. Closing a teardown by hand is now an override with a reason."""
import uuid
from datetime import date

from django.contrib.contenttypes.models import ContentType

from Tracker.models import Core, PartTypes, RecordEdit
from Tracker.presets import GROUP_PRESETS
from Tracker.services.reman.core import override_teardown_completion
from Tracker.services.reman.core_part import create_core
from Tracker.tests.base import TenantTestCase

ACTIONS = ('request_authorisation', 'release_to_rebuild', 'release_to_inventory', 'complete_disassembly')


def _perms(name):
    return list(next(p['permissions'] for p in GROUP_PRESETS.values() if p['name'] == name))


class CoreDecisionGateTests(TenantTestCase):

    def _as(self, group):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, _perms(group))
        self.authenticate_as(self.user_a, self.tenant_a)

    def _status(self, action):
        # The gate is checked before the core is looked up: 403 refused, 404 let through.
        return self.client.post(f"/api/Cores/{uuid.uuid4()}/{action}/", {"reason": "x"},
                                format="json").status_code

    def test_an_operator_is_refused_each_decision(self):
        self._as('Operator')
        for action in ACTIONS:
            self.assertEqual(self._status(action), 403, action)

    def test_a_shift_lead_passes_each_gate(self):
        self._as('Shift Lead')
        for action in ACTIONS:
            self.assertEqual(self._status(action), 404, action)

    def test_operators_keep_routine_capture(self):
        self.assertIn('change_core', _perms('Operator'))
        self.assertNotIn('complete_disassembly', _perms('Operator'))
        for group in ('Shift Lead', 'Production Manager', 'Planner', 'Tenant Admin'):
            for perm in ('request_core_authorisation', 'release_core', 'complete_disassembly'):
                self.assertIn(perm, _perms(group), (group, perm))


class ScrapCoreGateTests(TenantTestCase):
    """Who may scrap a core is the shop's choice: its own perm, not the POST default
    (add_core), which receiving needs. Granted to the same groups as add_core."""

    def _scrap(self, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.post(f"/api/Cores/{uuid.uuid4()}/scrap/", {"reason": "x"},
                                format="json").status_code

    def test_add_core_alone_does_not_scrap(self):
        self.assertEqual(self._scrap(['view_core', 'add_core', 'change_core']), 403)

    def test_scrap_core_is_the_gate(self):
        self.assertEqual(self._scrap(['view_core', 'scrap_core']), 404)

    def test_defaults_are_unchanged(self):
        holders = lambda perm: {p['name'] for p in GROUP_PRESETS.values() if perm in p['permissions']}
        self.assertEqual(holders('scrap_core'), holders('add_core'))


class TeardownOverrideTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector core", ID_prefix="C")
        self.core = create_core(tenant=self.tenant_a, core_type=pt, received_date=date.today(),
                                received_by=self.user_a, condition_grade='A', status='IN_DISASSEMBLY')

    def test_a_reason_is_required(self):
        with self.assertRaisesMessage(ValueError, "Say why"):
            override_teardown_completion(self.core, self.user_a, "  ")
        self.core.refresh_from_db()
        self.assertEqual(self.core.status, 'IN_DISASSEMBLY')

    def test_the_reason_is_recorded_with_the_person(self):
        override_teardown_completion(self.core, self.user_a, "Remaining steps don't apply to this unit")
        self.core.refresh_from_db()
        self.assertEqual(self.core.status, 'DISASSEMBLED')
        edit = RecordEdit.objects.get(content_type=ContentType.objects.get_for_model(Core),
                                      object_id=self.core.id, field_name='status')
        self.assertEqual((edit.old_value, edit.new_value, edit.edited_by_id),
                         ('IN_DISASSEMBLY', 'DISASSEMBLED', self.user_a.id))
        self.assertEqual(edit.reason, "Remaining steps don't apply to this unit")
