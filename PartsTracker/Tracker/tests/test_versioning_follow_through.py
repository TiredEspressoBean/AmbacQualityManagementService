"""
Versioning follow-through: configuration follows a versioned row to its new
version; history stays on the version where it happened.

Covers:
- Equipments: `operating_shifts` M2M, StepEquipmentAffinity, WorkCenterChangeover,
  ContinuousMachine, and current WorkCenter membership move to the new version;
  CalibrationRecord stays.
- TrainingType: TrainingRequirement moves to the new version; TrainingRecord
  stays, and qualification reads (authorization, qualified users, matrix,
  expiry supersession) compare across the version chain.
- TrainingTypeViewSet: list shows current versions only; retrieve of an old
  version by id keeps working.
"""
from datetime import date, time, timedelta

from rest_framework.test import APIRequestFactory

from Tracker.models import (
    CalibrationRecord,
    CompetencyLevel,
    ContinuousMachine,
    Equipments,
    PartTypes,
    Shift,
    StepEquipmentAffinity,
    Steps,
    TrainingRecord,
    TrainingRequirement,
    TrainingType,
    WorkCenter,
    WorkCenterChangeover,
)
from Tracker.serializers.mes_lite import EquipmentsSerializer
from Tracker.serializers.training import TrainingTypeSerializer
from Tracker.services.training import (
    _training_superseded,
    build_training_matrix,
    check_training_authorization,
    get_qualified_users_for_step,
    get_user_current_levels,
)
from Tracker.tests.base import TenantTestCase


def _serializer_save(serializer_cls, instance, data, user):
    request = APIRequestFactory().patch('/')
    request.user = user
    s = serializer_cls(instance, data=data, partial=True, context={'request': request})
    s.is_valid(raise_exception=True)
    return s.save()


# =============================================================================
# Equipment
# =============================================================================

class EquipmentVersionFollowThroughTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.day = Shift.objects.create(
            name='Day', code='DAY', start_time=time(6), end_time=time(14))
        self.night = Shift.objects.create(
            name='Night', code='NGT', start_time=time(22), end_time=time(6))
        self.machine = Equipments.objects.create(
            name='CNC-1', serial_number='C-1', is_schedulable=True)
        self.machine.operating_shifts.set([self.day, self.night])

        pt = PartTypes.objects.create(name='Bracket')
        self.op10 = Steps.objects.create(name='Mill', part_type=pt)
        self.op20 = Steps.objects.create(name='Drill', part_type=pt)

    def _version(self, **changes):
        return _serializer_save(EquipmentsSerializer, self.machine, changes, self.user_a)

    def test_content_edit_keeps_operating_shifts(self):
        new = self._version(name='CNC-1A')
        self.assertEqual(new.version, 2)
        self.assertEqual(set(new.operating_shifts.all()), {self.day, self.night})

    def test_direct_create_new_version_keeps_operating_shifts(self):
        """The import path calls create_new_version directly, not the serializer."""
        new = self.machine.create_new_version(name='CNC-1B')
        self.assertEqual(set(new.operating_shifts.all()), {self.day, self.night})

    def test_explicit_operating_shifts_override_wins(self):
        new = self.machine.create_new_version(name='CNC-1C', operating_shifts=[self.day])
        self.assertEqual(list(new.operating_shifts.all()), [self.day])

    def test_step_affinities_follow_the_machine(self):
        aff = StepEquipmentAffinity.objects.create(
            step=self.op10, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED, cycle_time_override=2.5)
        new = self._version(name='CNC-1A')
        aff.refresh_from_db()
        self.assertEqual(aff.equipment_id, new.id)
        self.assertEqual(aff.cycle_time_override, 2.5)
        self.assertFalse(StepEquipmentAffinity.objects.filter(equipment=self.machine).exists())

    def test_changeovers_follow_the_machine(self):
        co = WorkCenterChangeover.objects.create(
            equipment=self.machine, from_step=self.op10, to_step=self.op20,
            changeover_minutes=45)
        new = self._version(name='CNC-1A')
        co.refresh_from_db()
        self.assertEqual(co.equipment_id, new.id)
        self.assertEqual(co.changeover_minutes, 45)

    def test_continuous_profile_follows_the_machine(self):
        prof = ContinuousMachine.objects.create(equipment=self.machine, parts_per_hour=120)
        new = self._version(name='CNC-1A')
        prof.refresh_from_db()
        self.assertEqual(prof.equipment_id, new.id)

    def test_current_work_centre_lists_the_new_version(self):
        wc = WorkCenter.objects.create(name='Machining', code='MC1')
        wc.equipment.add(self.machine)
        new = self._version(name='CNC-1A')
        self.assertEqual(list(wc.equipment.all()), [new])

    def test_calibration_history_stays_on_the_old_version(self):
        cal = CalibrationRecord.objects.create(
            equipment=self.machine,
            calibration_date=date.today() - timedelta(days=10),
            due_date=date.today() + timedelta(days=355),
            result=CalibrationRecord.CalibrationResult.PASS,
        )
        self._version(name='CNC-1A')
        cal.refresh_from_db()
        self.assertEqual(cal.equipment_id, self.machine.id)


# =============================================================================
# TrainingType
# =============================================================================

class TrainingTypeVersionFollowThroughTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.cmm = TrainingType.objects.create(name='CMM Operation', validity_period_days=365)
        pt = PartTypes.objects.create(name='Housing')
        self.step = Steps.objects.create(name='Inspect', part_type=pt)
        self.req = TrainingRequirement.objects.create(
            training_type=self.cmm, step=self.step, min_level=CompetencyLevel.QUALIFIED)
        self.record = TrainingRecord.objects.create(
            user=self.user_a, training_type=self.cmm,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED)

    def _version(self, **changes):
        return _serializer_save(TrainingTypeSerializer, self.cmm, changes, self.user_a)

    def test_requirement_follows_record_stays(self):
        new = self._version(description='Rev B curriculum')
        self.assertEqual(new.version, 2)
        self.req.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(self.req.training_type_id, new.id)
        self.assertEqual(self.record.training_type_id, self.cmm.id)

    def test_authorization_still_passes_after_versioning(self):
        self.assertTrue(check_training_authorization(self.user_a, self.step).authorized)
        self._version(description='Rev B curriculum')
        result = check_training_authorization(self.user_a, self.step)
        self.assertTrue(result.authorized, result.to_dict())

    def test_qualified_users_survive_versioning(self):
        self._version(description='Rev B curriculum')
        self.assertIn(self.user_a, list(get_qualified_users_for_step(self.step)))

    def test_levels_fold_across_versions(self):
        """A level-2 record on v1 and a level-4 record on v2 are one training."""
        self.record.level = CompetencyLevel.QUALIFIED - 1
        self.record.save()
        new = self._version(description='Rev B curriculum')
        TrainingRecord.objects.create(
            user=self.user_a, training_type=new,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED + 1)
        levels = get_user_current_levels(self.user_a)
        self.assertEqual(len(levels), 1)
        self.assertEqual(next(iter(levels.values()))[0], CompetencyLevel.QUALIFIED + 1)

    def test_expired_old_version_record_reported_as_expired(self):
        self.record.completed_date = date.today() - timedelta(days=400)
        self.record.expires_date = date.today() - timedelta(days=35)
        self.record.save()
        self._version(description='Rev B curriculum')
        result = check_training_authorization(self.user_a, self.step)
        self.assertFalse(result.authorized)
        self.assertIn('Expired', result.missing[0][1])

    def test_renewal_on_new_version_supersedes_old_record(self):
        self.record.expires_date = date.today() + timedelta(days=20)
        self.record.save()
        new = self._version(description='Rev B curriculum')
        TrainingRecord.objects.create(
            user=self.user_a, training_type=new,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED)
        self.assertTrue(_training_superseded(self.record))

    def test_matrix_has_one_column_per_type_and_folds_records(self):
        new = self._version(description='Rev B curriculum')
        matrix = build_training_matrix(tenant=self.tenant_a)
        cmm_cols = [t for t in matrix['training_types'] if t['name'] == 'CMM Operation']
        self.assertEqual(cmm_cols, [{'id': str(new.id), 'name': 'CMM Operation'}])
        op = next(o for o in matrix['operators'] if o['id'] == self.user_a.id)
        cells = [c for c in op['cells'] if c['training_type'] == str(new.id)]
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]['level'], CompetencyLevel.QUALIFIED)


class TrainingTypeListCurrentOnlyTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.obj = TrainingType.objects.create(name='Soldering IPC-A-610')
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ['view_trainingtype', 'full_tenant_access'])
        self.authenticate_as(self.user_a)

    def test_list_returns_only_current_version(self):
        new = _serializer_save(
            TrainingTypeSerializer, self.obj, {'description': 'Rev B'}, self.user_a)
        resp = self.client.get('/api/TrainingTypes/', {'limit': 100})
        self.assertEqual(resp.status_code, 200)
        rows = [r for r in resp.data['results'] if r['name'] == 'Soldering IPC-A-610']
        self.assertEqual([r['id'] for r in rows], [str(new.id)])

    def test_superseded_version_retrievable_by_id(self):
        old_id = self.obj.id
        _serializer_save(TrainingTypeSerializer, self.obj, {'description': 'Rev B'}, self.user_a)
        resp = self.client.get(f'/api/TrainingTypes/{old_id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['version'], 1)
