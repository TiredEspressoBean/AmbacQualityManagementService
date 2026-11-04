"""Serializers for cycle counts (services/mes/cycle_count.py)."""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import CycleCount
from Tracker.serializers.core import SecureModelMixin

LINE_KINDS = [('LOT', 'Lot'), ('PART', 'Unit')]
VARIANCES = [('SHORT', 'Short'), ('OVER', 'Over'), ('MISSING', 'Not found'), ('FOUND_HERE', 'Found here')]


def _reasons():
    from Tracker.services.mes.cycle_count import REASONS
    return REASONS


# Why the record was off (services/mes/cycle_count.REASONS).
COUNT_REASONS = _reasons()


class CycleCountLineSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=LINE_KINDS)
    id = serializers.CharField()
    label = serializers.CharField()
    item = serializers.CharField(allow_blank=True)
    unit = serializers.CharField(allow_blank=True)
    # Null while a blind count is open: the counter counts rather than confirms.
    expected = serializers.FloatField(allow_null=True)
    counted = serializers.FloatField(allow_null=True)
    found_here = serializers.BooleanField()
    system_location = serializers.CharField(allow_blank=True, allow_null=True)
    location_id = serializers.CharField(allow_null=True, required=False,
                                        help_text="Where UQMES had it.")
    found_at = serializers.CharField(allow_null=True, required=False,
                                     help_text="Where a found item was (an item count spans locations).")
    note = serializers.CharField(allow_blank=True)


class CycleCountVarianceSerializer(CycleCountLineSerializer):
    difference = serializers.FloatField()
    variance = serializers.ChoiceField(choices=VARIANCES)
    abc_class = serializers.ChoiceField(choices=[('A', 'A'), ('B', 'B'), ('C', 'C')])
    tolerance = serializers.FloatField(help_text="The difference allowed for its class, in units.")
    within_tolerance = serializers.BooleanField(
        help_text="False: a miss — usually recounted; applying it anyway needs a note.")
    reason = serializers.ChoiceField(choices=[('', '—'), *COUNT_REASONS], allow_blank=True,
                                     help_text="Why the record was off, given when applied.")


class ApplyCountSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True,
                                 help_text="Required when lines are outside tolerance: why the "
                                           "difference is real rather than recounted.")
    reasons = serializers.DictField(
        child=serializers.ChoiceField(choices=COUNT_REASONS), required=False,
        help_text='A reason code per difference, keyed "LOT:<id>" / "PART:<id>". Every '
                  'difference needs one.')


class MissingUnitSerializer(serializers.Serializer):
    """A unit a count didn't find, still unresolved."""
    count_id = serializers.UUIDField()
    count_number = serializers.CharField()
    scope = serializers.CharField()
    applied_at = serializers.DateTimeField()
    part_id = serializers.UUIDField()
    serial = serializers.CharField()
    item = serializers.CharField(allow_blank=True)
    expected_at = serializers.CharField(allow_blank=True)
    reason = serializers.CharField(allow_blank=True)
    status = serializers.CharField()


class ResolveMissingSerializer(serializers.Serializer):
    part = serializers.UUIDField()
    note = serializers.CharField(help_text="What became of it.")


class MarkKeyedSerializer(serializers.Serializer):
    counts = serializers.ListField(child=serializers.UUIDField(),
                                   help_text="The applied counts whose differences were keyed into the ERP.")


ABC = [('A', 'A'), ('B', 'B'), ('C', 'C')]


class DueLocationSerializer(serializers.Serializer):
    location_id = serializers.UUIDField()
    location = serializers.CharField()
    last_counted = serializers.DateTimeField(allow_null=True)
    due_on = serializers.DateField()


class DueForCountSerializer(serializers.Serializer):
    """An item whose stock somewhere is due for counting under its ABC class."""
    kind = serializers.ChoiceField(choices=[('MATERIAL', 'Material'), ('PART_TYPE', 'Part type')])
    id = serializers.UUIDField()
    name = serializers.CharField()
    abc_class = serializers.ChoiceField(choices=ABC)
    interval_days = serializers.IntegerField()
    due_on = serializers.DateField()
    days_overdue = serializers.IntegerField()
    never_counted = serializers.BooleanField()
    locations = DueLocationSerializer(many=True)


class ClassAccuracySerializer(serializers.Serializer):
    counted = serializers.IntegerField()
    hits = serializers.IntegerField()
    pct = serializers.FloatField(allow_null=True)


class CountAccuracySerializer(serializers.Serializer):
    """Inventory record accuracy per ABC class: counted lines within tolerance; and the
    differences by the reason the lead gave."""
    days = serializers.IntegerField()
    A = ClassAccuracySerializer()
    B = ClassAccuracySerializer()
    C = ClassAccuracySerializer()
    by_reason = serializers.DictField(child=serializers.IntegerField())


def _name(u):
    return ((u.get_full_name() or "").strip() or u.email) if u is not None else None


class CycleCountSerializer(SecureModelMixin):
    """A count of one location. Started by POST (location, blind); counted, submitted and
    applied through its actions."""
    lines = serializers.SerializerMethodField()
    variances = serializers.SerializerMethodField()
    not_counted = serializers.SerializerMethodField()
    started_by_name = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    applied_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True, allow_null=True,
                                          default=None)
    scope_name = serializers.CharField(read_only=True, help_text="What's counted: the location or the item.")
    scope = serializers.SerializerMethodField()
    erp_keyed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CycleCount
        fields = (
            'id', 'count_number', 'location', 'location_name', 'material', 'part_type',
            'scope', 'scope_name', 'blind', 'status', 'status_display',
            'lines', 'variances', 'not_counted',
            'started_by', 'started_by_name', 'submitted_by_name', 'submitted_at',
            'applied_by_name', 'applied_at', 'apply_note', 'erp_keyed_at', 'erp_keyed_by_name',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('count_number', 'location', 'material', 'part_type', 'status', 'started_by',
                            'submitted_at', 'applied_at', 'apply_note', 'erp_keyed_at',
                            'created_at', 'updated_at')

    @extend_schema_field(CycleCountLineSerializer(many=True))
    def get_lines(self, obj):
        hide = obj.blind and obj.status == 'OPEN'
        return CycleCountLineSerializer(
            [{**l, "expected": None if hide else l.get("expected")} for l in obj.lines], many=True).data

    @extend_schema_field(CycleCountVarianceSerializer(many=True))
    def get_variances(self, obj):
        from Tracker.services.mes.cycle_count import variances
        if obj.status == 'OPEN':
            return []
        return CycleCountVarianceSerializer(variances(obj), many=True).data

    @extend_schema_field(serializers.IntegerField(
        help_text="Lines left blank: not counted, so left out of the differences and never applied."))
    def get_not_counted(self, obj):
        from Tracker.services.mes.cycle_count import not_counted
        return not_counted(obj)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_started_by_name(self, obj):
        return _name(obj.started_by)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_submitted_by_name(self, obj):
        return _name(obj.submitted_by)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_applied_by_name(self, obj):
        return _name(obj.applied_by)

    @extend_schema_field(serializers.ChoiceField(choices=[('LOCATION', 'Location'), ('MATERIAL', 'Material'),
                                                          ('PART_TYPE', 'Part type')]))
    def get_scope(self, obj):
        return 'LOCATION' if obj.location_id else 'MATERIAL' if obj.material_id else 'PART_TYPE'

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_erp_keyed_by_name(self, obj):
        return _name(obj.erp_keyed_by)


class SendBackCountSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, help_text="Why it's going back for a recount.")


class StartCycleCountSerializer(serializers.Serializer):
    """What to count: one location, or one material or part type wherever it's kept."""
    location = serializers.CharField(required=False, allow_blank=True,
                                     help_text="The location's id, code or name (a scanned LOC: label is fine).")
    material = serializers.UUIDField(required=False, allow_null=True)
    part_type = serializers.UUIDField(required=False, allow_null=True)
    blind = serializers.BooleanField(required=False, default=False)


class CountEntrySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=LINE_KINDS)
    id = serializers.UUIDField()
    counted = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)
    found_at = serializers.CharField(required=False, allow_blank=True,
                                     help_text="An item count's found item: where it was (location id, code or name).")


class RecordCountSerializer(serializers.Serializer):
    entries = CountEntrySerializer(many=True)
