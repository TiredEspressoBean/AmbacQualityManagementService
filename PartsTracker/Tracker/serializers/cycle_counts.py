"""Serializers for cycle counts (services/mes/cycle_count.py)."""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import CycleCount
from Tracker.serializers.core import SecureModelMixin

LINE_KINDS = [('LOT', 'Lot'), ('PART', 'Unit')]
VARIANCES = [('SHORT', 'Short'), ('OVER', 'Over'), ('MISSING', 'Not found'), ('FOUND_HERE', 'Found here')]


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
    note = serializers.CharField(allow_blank=True)


class CycleCountVarianceSerializer(CycleCountLineSerializer):
    difference = serializers.FloatField()
    variance = serializers.ChoiceField(choices=VARIANCES)


def _name(u):
    return ((u.get_full_name() or "").strip() or u.email) if u is not None else None


class CycleCountSerializer(SecureModelMixin):
    """A count of one location. Started by POST (location, blind); counted, submitted and
    applied through its actions."""
    lines = serializers.SerializerMethodField()
    variances = serializers.SerializerMethodField()
    started_by_name = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    applied_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = CycleCount
        fields = (
            'id', 'count_number', 'location', 'location_name', 'blind', 'status', 'status_display',
            'lines', 'variances',
            'started_by', 'started_by_name', 'submitted_by_name', 'submitted_at',
            'applied_by_name', 'applied_at', 'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('count_number', 'location', 'status', 'started_by', 'submitted_at', 'applied_at',
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

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_started_by_name(self, obj):
        return _name(obj.started_by)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_submitted_by_name(self, obj):
        return _name(obj.submitted_by)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_applied_by_name(self, obj):
        return _name(obj.applied_by)


class StartCycleCountSerializer(serializers.Serializer):
    location = serializers.CharField(help_text="The location's id, code or name (a scanned LOC: label is fine).")
    blind = serializers.BooleanField(required=False, default=False)


class CountEntrySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=LINE_KINDS)
    id = serializers.UUIDField()
    counted = serializers.DecimalField(max_digits=14, decimal_places=4, required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class RecordCountSerializer(serializers.Serializer):
    entries = CountEntrySerializer(many=True)
