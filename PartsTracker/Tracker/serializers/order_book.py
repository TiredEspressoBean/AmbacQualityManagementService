"""HTTP shapes for the order book (services/mes/order_book DTOs). Plain serializers —
read-only, built from frozen dataclasses."""
from rest_framework import serializers


class OrderBlockerSerializer(serializers.Serializer):
    kind = serializers.CharField()
    label = serializers.CharField()
    link = serializers.CharField()


class OrderProgressSerializer(serializers.Serializer):
    ordered = serializers.IntegerField()
    planned = serializers.IntegerField()
    in_work = serializers.IntegerField()
    done = serializers.IntegerField()
    shipped = serializers.IntegerField()


class OrderProjectionSerializer(serializers.Serializer):
    due = serializers.DateField(allow_null=True)
    projected = serializers.DateField(allow_null=True)
    slip_days = serializers.IntegerField(allow_null=True)
    state = serializers.ChoiceField(choices=["late", "on_track", "not_scheduled"])


class OrderBookRowSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    order_number = serializers.CharField()
    name = serializers.CharField()
    customer_name = serializers.CharField(allow_null=True)
    earliest_due = serializers.DateField(allow_null=True)
    unplanned = serializers.IntegerField()
    projection = OrderProjectionSerializer()
    blockers = OrderBlockerSerializer(many=True)
    more_blockers = serializers.IntegerField()
    progress = OrderProgressSerializer()
    at_risk = serializers.BooleanField()


class OnTimeDeliverySerializer(serializers.Serializer):
    days = serializers.IntegerField()
    deliveries = serializers.IntegerField()
    on_time = serializers.IntegerField()
    on_time_pct = serializers.FloatField(allow_null=True)
    unmeasured = serializers.IntegerField()


class OrderBookSerializer(serializers.Serializer):
    rows = OrderBookRowSerializer(many=True)
    on_time = OnTimeDeliverySerializer()


class OrderLineViewSerializer(serializers.Serializer):
    line_id = serializers.CharField()
    line_number = serializers.IntegerField()
    part_type_id = serializers.CharField()
    part_type_name = serializers.CharField()
    quantity = serializers.IntegerField()
    remaining = serializers.IntegerField()
    due_date = serializers.DateField(allow_null=True)
    status = serializers.CharField()
    progress = OrderProgressSerializer()


class OrderWorkOrderViewSerializer(serializers.Serializer):
    work_order_id = serializers.CharField()
    erp_id = serializers.CharField()
    status = serializers.CharField()
    released = serializers.BooleanField()
    due = serializers.DateField(allow_null=True)
    projection = OrderProjectionSerializer()
    blockers = OrderBlockerSerializer(many=True)
    units = serializers.ListField(
        child=serializers.CharField(),
        help_text="Set when the work order isn't the order's own: the order's units on it.")


class OrderShipmentViewSerializer(serializers.Serializer):
    shipment_id = serializers.CharField()
    shipment_number = serializers.CharField()
    shipped_at = serializers.DateField(allow_null=True)
    line_number = serializers.IntegerField(allow_null=True)
    quantity = serializers.IntegerField()
    on_time = serializers.BooleanField(allow_null=True)


class OrderDetailSerializer(serializers.Serializer):
    row = OrderBookRowSerializer()
    original_completion = serializers.DateField(allow_null=True)
    estimated_completion = serializers.DateField(allow_null=True)
    lines = OrderLineViewSerializer(many=True)
    work_orders = OrderWorkOrderViewSerializer(many=True)
    shipments = OrderShipmentViewSerializer(many=True)
    ready_to_ship = serializers.IntegerField()
