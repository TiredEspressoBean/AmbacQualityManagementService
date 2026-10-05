"""Serializers for recorded moves, location views and scan lookup
(services/mes/locations.py, services/core/scan.py)."""
from decimal import Decimal

from rest_framework import serializers


class MoveLotRequestSerializer(serializers.Serializer):
    to = serializers.CharField(help_text="Destination location: its id, code or name; a scanned LOC: label is fine.")
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=Decimal('0.0001'), required=False, allow_null=True,
        help_text="Move only this much (split off first). Omit to move the whole lot.")
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class MovePartsRequestSerializer(serializers.Serializer):
    part_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    to = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class MovePartsResultSerializer(serializers.Serializer):
    moved = serializers.IntegerField()


from Tracker.models.mes_standard import STORAGE_LOCATION_KINDS as _KIND_CHOICES  # noqa: E402


class LocationSummarySerializer(serializers.Serializer):
    """One row of the location tree. ``lots``/``parts``/``equipment`` count what is in
    the location itself; ``total_*`` add everything inside it."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    path = serializers.CharField()
    depth = serializers.IntegerField()
    parent = serializers.UUIDField(allow_null=True)
    kind = serializers.ChoiceField(choices=_KIND_CHOICES)
    code = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()
    held_only = serializers.BooleanField()
    receiving_dock = serializers.BooleanField()
    lots = serializers.IntegerField()
    parts = serializers.IntegerField()
    equipment = serializers.IntegerField()
    total_lots = serializers.IntegerField()
    total_parts = serializers.IntegerField()
    total_equipment = serializers.IntegerField()


class LocationLotSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    lot_number = serializers.CharField()
    item_name = serializers.CharField(allow_null=True, allow_blank=True)
    quantity_remaining = serializers.FloatField()
    unit_of_measure = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    owner_name = serializers.CharField(allow_null=True)
    sublocation = serializers.CharField(allow_null=True, help_text="Set when it is in a location inside this one.")


class LocationPartSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    erp_id = serializers.CharField()
    part_type = serializers.CharField(allow_null=True)
    work_order_id = serializers.UUIDField(allow_null=True)
    work_order = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    sublocation = serializers.CharField(allow_null=True)


class LocationEquipmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    serial_number = serializers.CharField(allow_blank=True)
    equipment_type = serializers.CharField(allow_null=True)
    sublocation = serializers.CharField(allow_null=True)


class LocationChildSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class LocationMoveSerializer(serializers.Serializer):
    at = serializers.DateTimeField()
    direction = serializers.ChoiceField(choices=[('IN', 'In'), ('OUT', 'Out')])
    kind = serializers.ChoiceField(choices=[('LOT', 'Lot'), ('PART', 'Part')])
    object_id = serializers.UUIDField()
    label = serializers.CharField()
    other = serializers.CharField(allow_blank=True)
    by = serializers.CharField(allow_null=True)


class LocationContentsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    path = serializers.CharField()
    kind = serializers.ChoiceField(choices=_KIND_CHOICES)
    code = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()
    held_only = serializers.BooleanField()
    receiving_dock = serializers.BooleanField()
    parent = serializers.UUIDField(allow_null=True)
    children = LocationChildSerializer(many=True)
    lots = LocationLotSerializer(many=True)
    parts = LocationPartSerializer(many=True)
    equipment = LocationEquipmentSerializer(many=True)
    moves = LocationMoveSerializer(many=True)


class ScanResultSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[
        ('LOT', 'Lot'), ('PART', 'Part'), ('WORK_ORDER', 'Work order'),
        ('LOCATION', 'Location'), ('URL', 'Page')])
    id = serializers.CharField(allow_blank=True)
    label = serializers.CharField()
    detail = serializers.CharField(allow_blank=True)
    path = serializers.CharField(allow_blank=True)
    item_id = serializers.CharField(allow_null=True)
    work_order_id = serializers.CharField(allow_null=True, required=False)
