"""Serializers for the scheduler's setup data as standalone resources.

The solver reads three tables of master data besides the routing itself: a step's
standard times (`StepTiming`), which machines can run a step (`StepEquipmentAffinity`),
and the minutes to switch a machine from one step to another (`WorkCenterChangeover`).
These give each one a CRUD surface of its own, mainly so a planner can maintain them
from a spreadsheet (import / export).

`StepTimingSerializer` in mes_lite.py is the NESTED shape (no `id`, no `step`) used on
the Steps serializer; it is left as it is. The standalone one here carries the step.

All three inherit `SecureModelMixin`, so a step / machine ID from another tenant is
rejected rather than linked.
"""
from rest_framework import serializers

from Tracker.models.scheduling import (
    StepEquipmentAffinity, StepTiming, WorkCenterChangeover,
)
from Tracker.serializers.core import SecureModelMixin


class StepTimingRecordSerializer(SecureModelMixin):
    """One step's standard times — setup, cycle, load/unload, attention, SMED setup."""
    step_name = serializers.CharField(source='step.name', read_only=True)

    class Meta:
        model = StepTiming
        fields = ('id', 'step', 'step_name', 'setup_minutes', 'cycle_time_minutes',
                  'load_unload_per_piece', 'attention_type', 'external_setup_minutes', 'archived')
        read_only_fields = ('id', 'step_name')


TIMING_SOURCES = ['authored', 'measured', 'expected', 'none']


class MeasuredStepTimingSerializer(serializers.Serializer):
    """A step's measured aspects beside what the scheduler uses for each
    (services/scheduling/measured.compare_step_timings). Read only."""
    step = serializers.UUIDField(source='step_id')
    step_name = serializers.CharField()
    runs = serializers.IntegerField(source='measured.runs')
    pieces = serializers.IntegerField(source='measured.pieces')
    per_piece_minutes = serializers.FloatField(source='measured.per_piece_minutes', allow_null=True)
    setup_minutes = serializers.FloatField(source='measured.setup_minutes', allow_null=True)
    method = serializers.ChoiceField(choices=['fit', 'average', 'none'], source='measured.method')
    note = serializers.CharField(source='measured.note', allow_blank=True)
    loads = serializers.IntegerField(source='measured.loads')
    cycle_per_load_minutes = serializers.FloatField(source='measured.cycle_per_load_minutes',
                                                    allow_null=True)
    setup_in_use = serializers.ChoiceField(choices=TIMING_SOURCES)
    cycle_in_use = serializers.ChoiceField(choices=TIMING_SOURCES)
    setup_drift = serializers.BooleanField()
    cycle_drift = serializers.BooleanField()
    drift_pct = serializers.IntegerField()


class StepEquipmentAffinitySerializer(SecureModelMixin):
    """A machine that can run a step, how well, and optionally its own cycle time."""
    step_name = serializers.CharField(source='step.name', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)

    class Meta:
        model = StepEquipmentAffinity
        fields = ('id', 'step', 'step_name', 'equipment', 'equipment_name', 'affinity',
                  'cycle_time_override', 'archived')
        read_only_fields = ('id', 'step_name', 'equipment_name')


class WorkCenterChangeoverSerializer(SecureModelMixin):
    """One cell of a machine's changeover matrix: minutes to go from one step to another."""
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    from_step_name = serializers.CharField(source='from_step.name', read_only=True)
    to_step_name = serializers.CharField(source='to_step.name', read_only=True)

    class Meta:
        model = WorkCenterChangeover
        fields = ('id', 'equipment', 'equipment_name', 'from_step', 'from_step_name',
                  'to_step', 'to_step_name', 'changeover_minutes', 'archived')
        read_only_fields = ('id', 'equipment_name', 'from_step_name', 'to_step_name')
