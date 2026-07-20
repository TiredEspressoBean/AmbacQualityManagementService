"""Shift-note serializer — HTTP boundary for the shift-notes API.

Write path is thin (author/tenant set in the viewset's perform_create); the
read fields expose author/work-order labels and the current user's ack state so
the operator tile can render without extra round-trips.
"""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import ShiftNote
from Tracker.serializers.core import SecureModelMixin


class ShiftNoteAckRosterItem(serializers.Serializer):
    """One entry in a note's acknowledgment roster (typed for the FE)."""
    user_name = serializers.CharField()
    acknowledged_at = serializers.DateTimeField()


class ShiftNoteSerializer(SecureModelMixin):
    author_name = serializers.SerializerMethodField()
    work_order_erp_id = serializers.SerializerMethodField()
    # Whether the CURRENT request user has acknowledged this note.
    acknowledged = serializers.SerializerMethodField()
    ack_count = serializers.SerializerMethodField()
    # Author's roster: who has acknowledged, and how many the note targets.
    acknowledged_by = serializers.SerializerMethodField()
    audience_size = serializers.SerializerMethodField()
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = ShiftNote
        fields = (
            "id", "author", "author_name", "body", "audience_roles",
            "work_order", "work_order_erp_id", "priority", "acknowledgment_required",
            "effective_from", "effective_until",
            "is_locked", "acknowledged", "ack_count", "acknowledged_by", "audience_size",
            "is_voided", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "author", "author_name", "work_order_erp_id", "is_locked",
            "acknowledged", "ack_count", "acknowledged_by", "audience_size",
            "is_voided", "created_at", "updated_at",
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_work_order_erp_id(self, obj):
        return obj.work_order.ERP_id if obj.work_order_id else None

    @extend_schema_field(serializers.BooleanField())
    def get_acknowledged(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.acknowledgments.filter(user=request.user).exists()

    @extend_schema_field(serializers.IntegerField())
    def get_ack_count(self, obj):
        return obj.acknowledgments.count()

    @extend_schema_field(ShiftNoteAckRosterItem(many=True))
    def get_acknowledged_by(self, obj):
        """Roster of who acknowledged — the compliance record for must-ack notes."""
        return [
            {
                "user_name": a.user.get_full_name() or a.user.email,
                "acknowledged_at": a.acknowledged_at.isoformat(),
            }
            for a in obj.acknowledgments.select_related("user").all()
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_audience_size(self, obj):
        """How many users the note targets (for the 'N of M acknowledged' readout)."""
        from Tracker.services.mes.shift_notes import audience_user_ids
        return len(audience_user_ids(obj.tenant, obj.audience_roles))
