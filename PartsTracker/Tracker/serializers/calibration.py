# serializers/calibration.py - Calibration Management Serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import CalibrationRecord
from .core import SecureModelMixin


class CalibrationRecordSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for CalibrationRecord model.

    Records a calibration event for a piece of equipment.
    Includes computed status properties and equipment info.
    """
    # Display/info fields
    equipment_info = serializers.SerializerMethodField()
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    calibration_type_display = serializers.CharField(source='get_calibration_type_display', read_only=True)

    # Computed status properties from model
    status = serializers.CharField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = CalibrationRecord
        fields = [
            'id', 'equipment', 'equipment_info',
            # Core calibration data
            'calibration_date', 'due_date', 'result', 'result_display',
            'calibration_type', 'calibration_type_display',
            # Who performed it
            'performed_by', 'external_lab',
            # Traceability
            'certificate_number', 'standards_used',
            # As-found/As-left
            'as_found_in_tolerance', 'adjustments_made',
            # Notes
            'notes',
            # Computed status
            'status', 'is_current', 'days_until_due', 'days_overdue',
            # Timestamps
            'created_at', 'updated_at', 'archived'
        ]
        read_only_fields = (
            'id', 'status', 'is_current', 'days_until_due', 'days_overdue',
            'result_display', 'calibration_type_display',
            'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_equipment_info(self, obj):
        """Return equipment details for this calibration record."""
        if obj.equipment:
            return {
                'id': obj.equipment.id,
                'name': obj.equipment.name,
                'serial_number': obj.equipment.serial_number if hasattr(obj.equipment, 'serial_number') else None,
                'equipment_type': obj.equipment.equipment_type.name if obj.equipment.equipment_type else None,
                'equipment_type_id': obj.equipment.equipment_type.id if obj.equipment.equipment_type else None,
            }
        return None


class CalibrationStatsSerializer(serializers.Serializer):
    """
    Serializer for calibration statistics response.
    """
    total_equipment = serializers.IntegerField()
    current_calibrations = serializers.IntegerField()
    due_soon = serializers.IntegerField()
    overdue = serializers.IntegerField()
    compliance_rate = serializers.FloatField()
