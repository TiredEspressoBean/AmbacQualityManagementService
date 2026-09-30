"""`GET /<endpoint>/{id}/version-history/` for a versioned model: every revision of the
row, oldest first, for an edit page's Revisions panel.

A revision is a separate row (`previous_version` chain), so a record's history is
its chain, not the audit entries of one id. The panel reads each revision's audit
entries itself.
"""
from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response


class VersionSummarySerializer(serializers.Serializer):
    """One revision of a versioned row."""
    id = serializers.CharField()
    version = serializers.IntegerField()
    is_current_version = serializers.BooleanField()
    archived = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    change_description = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_change_description(self, obj):
        # Only models with a concrete field keep the reason given for a revision.
        return getattr(obj, 'change_description', None) or None


class VersionHistoryMixin:
    @extend_schema(responses=VersionSummarySerializer(many=True))
    @action(detail=True, methods=['get'], url_path='version-history', pagination_class=None)
    def version_history(self, request, pk=None):
        """Every revision of this row, oldest first."""
        obj = self.get_object()
        return Response(VersionSummarySerializer(obj.get_version_history(), many=True).data)
