"""Response shapes for the master migration workbook (services.core.master_workbook)."""
from rest_framework import serializers


class MasterWorkbookSheetInfoSerializer(serializers.Serializer):
    title = serializers.CharField()
    about = serializers.CharField()
    # Whether this user may load the sheet (add + change on its table).
    allowed = serializers.BooleanField()


class MasterWorkbookRowSerializer(serializers.Serializer):
    row = serializers.IntegerField(help_text="The spreadsheet row (the header is row 1).")
    outcome = serializers.ChoiceField(choices=["error", "warning", "note"])
    detail = serializers.CharField()


class MasterWorkbookSheetResultSerializer(serializers.Serializer):
    sheet = serializers.CharField()
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    unchanged = serializers.IntegerField()
    errors = serializers.IntegerField()
    rows = MasterWorkbookRowSerializer(many=True)
    detail = serializers.CharField(allow_blank=True)


class MasterWorkbookTotalsSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    unchanged = serializers.IntegerField()
    errors = serializers.IntegerField()


class MasterWorkbookResultSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField()
    loaded = serializers.BooleanField()
    totals = MasterWorkbookTotalsSerializer()
    sheets = MasterWorkbookSheetResultSerializer(many=True)
    ignored_sheets = serializers.ListField(child=serializers.CharField())


class MasterWorkbookQueuedSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    total_rows = serializers.IntegerField()


class MasterWorkbookProgressSerializer(serializers.Serializer):
    current = serializers.IntegerField()
    total = serializers.IntegerField()
    sheet = serializers.CharField(allow_blank=True)


class MasterWorkbookStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["PENDING", "PROGRESS", "SUCCESS", "FAILURE"])
    progress = MasterWorkbookProgressSerializer(allow_null=True)
    result = MasterWorkbookResultSerializer(allow_null=True)
    error = serializers.CharField(allow_blank=True)
