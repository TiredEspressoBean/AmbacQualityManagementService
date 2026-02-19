"""
SPC (Statistical Process Control) Serializers

Contains:
- SPCBaselineSerializer: Full serializer with all fields
- SPCBaselineListSerializer: Lightweight serializer for listing
- SPCBaselineFreezeSerializer: Serializer for freezing new baselines
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from Tracker.models import SPCBaseline, ChartType, BaselineStatus, MeasurementDefinition


class SPCBaselineSerializer(serializers.ModelSerializer):
    """Full SPC Baseline serializer with all fields and computed properties."""

    chart_type_display = serializers.CharField(source='get_chart_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frozen_by_name = serializers.SerializerMethodField()
    measurement_label = serializers.CharField(source='measurement_definition.label', read_only=True)
    process_name = serializers.SerializerMethodField()
    step_name = serializers.CharField(source='measurement_definition.step.name', read_only=True)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_process_name(self, obj):
        """Get process name from ProcessStep (step can be in multiple processes)."""
        if obj.measurement_definition and obj.measurement_definition.step:
            from Tracker.models import ProcessStep
            ps = ProcessStep.objects.filter(step=obj.measurement_definition.step).first()
            if ps and ps.process:
                return ps.process.name
        return None
    control_limits = serializers.DictField(read_only=True)

    class Meta:
        model = SPCBaseline
        fields = [
            'id',
            # Relationships
            'measurement_definition', 'measurement_label', 'process_name', 'step_name',
            # Chart config
            'chart_type', 'chart_type_display', 'subgroup_size',
            # X-bar limits
            'xbar_ucl', 'xbar_cl', 'xbar_lcl',
            'range_ucl', 'range_cl', 'range_lcl',
            # I-MR limits
            'individual_ucl', 'individual_cl', 'individual_lcl',
            'mr_ucl', 'mr_cl',
            # Status
            'status', 'status_display',
            # Tracking
            'frozen_by', 'frozen_by_name', 'frozen_at',
            'superseded_by', 'superseded_at', 'superseded_reason',
            # Metadata
            'sample_count', 'notes',
            'control_limits',
            # Audit
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'frozen_at', 'superseded_at', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_frozen_by_name(self, obj):
        if obj.frozen_by:
            name = f"{obj.frozen_by.first_name} {obj.frozen_by.last_name}".strip()
            return name or obj.frozen_by.username
        return None


class SPCBaselineListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing baselines."""

    chart_type_display = serializers.CharField(source='get_chart_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frozen_by_name = serializers.SerializerMethodField()
    measurement_label = serializers.CharField(source='measurement_definition.label', read_only=True)

    class Meta:
        model = SPCBaseline
        fields = [
            'id', 'measurement_definition', 'measurement_label',
            'chart_type', 'chart_type_display', 'subgroup_size',
            'status', 'status_display',
            'frozen_by', 'frozen_by_name', 'frozen_at',
            'sample_count',
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_frozen_by_name(self, obj):
        if obj.frozen_by:
            name = f"{obj.frozen_by.first_name} {obj.frozen_by.last_name}".strip()
            return name or obj.frozen_by.username
        return None


class SPCBaselineFreezeSerializer(serializers.Serializer):
    """
    Serializer for freezing a new baseline.

    Accepts the control limits calculated by the frontend and stores them.
    """

    measurement_definition_id = serializers.UUIDField()
    chart_type = serializers.ChoiceField(choices=ChartType.choices)
    subgroup_size = serializers.IntegerField(min_value=1, max_value=25)

    # X-bar limits (for XBAR_R and XBAR_S)
    xbar_ucl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    xbar_cl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    xbar_lcl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    range_ucl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    range_cl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    range_lcl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)

    # I-MR limits
    individual_ucl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    individual_cl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    individual_lcl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    mr_ucl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)
    mr_cl = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True)

    # Metadata
    sample_count = serializers.IntegerField(required=False, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_measurement_definition_id(self, value):
        if not MeasurementDefinition.objects.filter(id=value).exists():
            raise serializers.ValidationError("Measurement definition not found")
        return value

    def validate(self, attrs):
        chart_type = attrs.get('chart_type')

        if chart_type == ChartType.I_MR:
            # I-MR requires individual limits
            required = ['individual_ucl', 'individual_cl', 'individual_lcl']
            if not all(attrs.get(f) for f in required):
                raise serializers.ValidationError(
                    "I-MR chart type requires individual_ucl, individual_cl, individual_lcl"
                )
        else:
            # X-bar charts require xbar and range limits
            required = ['xbar_ucl', 'xbar_cl', 'xbar_lcl', 'range_ucl', 'range_cl']
            if not all(attrs.get(f) for f in required):
                raise serializers.ValidationError(
                    "X-bar chart types require xbar_ucl, xbar_cl, xbar_lcl, range_ucl, range_cl"
                )

        return attrs

    def create(self, validated_data):
        """Create a new baseline (automatically supersedes existing active baseline)."""
        user = self.context['request'].user

        baseline = SPCBaseline.objects.create(
            measurement_definition_id=validated_data['measurement_definition_id'],
            chart_type=validated_data['chart_type'],
            subgroup_size=validated_data['subgroup_size'],
            # X-bar limits
            xbar_ucl=validated_data.get('xbar_ucl'),
            xbar_cl=validated_data.get('xbar_cl'),
            xbar_lcl=validated_data.get('xbar_lcl'),
            range_ucl=validated_data.get('range_ucl'),
            range_cl=validated_data.get('range_cl'),
            range_lcl=validated_data.get('range_lcl'),
            # I-MR limits
            individual_ucl=validated_data.get('individual_ucl'),
            individual_cl=validated_data.get('individual_cl'),
            individual_lcl=validated_data.get('individual_lcl'),
            mr_ucl=validated_data.get('mr_ucl'),
            mr_cl=validated_data.get('mr_cl'),
            # Metadata
            sample_count=validated_data.get('sample_count', 0),
            notes=validated_data.get('notes', ''),
            # Tracking
            frozen_by=user,
            status=BaselineStatus.ACTIVE,
        )

        return baseline
