"""Shift-note serializer — HTTP boundary for the shift-notes API.

Write path is thin (author/tenant set in the viewset's perform_create); the
read fields expose author/work-order labels and the current user's ack state so
the operator tile can render without extra round-trips.
"""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import ShiftNote
from Tracker.serializers.core import SecureModelMixin


class ShiftNoteSerializer(SecureModelMixin):
    author_name = serializers.SerializerMethodField()
    work_order_erp_id = serializers.SerializerMethodField()
    # Whether the CURRENT request user has acknowledged this note.
    acknowledged = serializers.SerializerMethodField()
    ack_count = serializers.SerializerMethodField()
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = ShiftNote
        fields = (
            "id", "author", "author_name", "body", "audience_roles",
            "work_order", "work_order_erp_id", "priority",
            "effective_from", "effective_until",
            "is_locked", "acknowledged", "ack_count",
            "is_voided", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "author", "author_name", "work_order_erp_id", "is_locked",
            "acknowledged", "ack_count", "is_voided", "created_at", "updated_at",
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
