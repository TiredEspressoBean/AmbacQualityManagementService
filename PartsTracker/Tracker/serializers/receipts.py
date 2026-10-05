"""Receipts for the ERP — the rows of the receipts sheet, and marking them posted
(services.mes.receipt_export)."""
from rest_framework import serializers

ERP_STATUSES = ["Ready to post", "Awaiting decision", "Posted", "Changed since posted"]


class ReceiptRowSerializer(serializers.Serializer):
    lot_id = serializers.CharField()
    our_lot = serializers.CharField()
    po_number = serializers.CharField(allow_blank=True)
    po_line = serializers.CharField(allow_blank=True)
    received = serializers.DateField(allow_null=True)
    item = serializers.CharField(allow_blank=True)
    item_name = serializers.CharField(allow_blank=True)
    supplier = serializers.CharField(allow_blank=True)
    unit = serializers.CharField(allow_blank=True)
    received_qty = serializers.DecimalField(max_digits=12, decimal_places=4)
    accepted = serializers.DecimalField(max_digits=12, decimal_places=4)
    rejected = serializers.DecimalField(max_digits=12, decimal_places=4)
    awaiting_decision = serializers.DecimalField(max_digits=12, decimal_places=4)
    decision = serializers.CharField()
    erp_status = serializers.ChoiceField(choices=ERP_STATUSES)


class MarkReceiptsPostedSerializer(serializers.Serializer):
    lot_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class MarkReceiptsPostedResultSerializer(serializers.Serializer):
    marked = serializers.IntegerField(
        help_text="Deliveries marked posted. Ones still awaiting a decision are skipped.")
