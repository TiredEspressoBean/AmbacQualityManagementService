"""Serializers for customer shipments (services/mes/shipping.py)."""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import CustomerShipment, Parts
from Tracker.serializers.core import SecureModelMixin


class ShipmentPartSerializer(serializers.ModelSerializer):
    """One unit on a shipment."""
    part_type_name = serializers.CharField(source='part_type.name', read_only=True, allow_null=True)
    work_order_number = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()

    class Meta:
        model = Parts
        fields = ('id', 'ERP_id', 'part_type_name', 'work_order_number', 'order_number')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_work_order_number(self, obj):
        return obj.work_order.ERP_id if obj.work_order_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_order_number(self, obj):
        order = obj.order or (obj.work_order.related_order if obj.work_order_id else None)
        return (order.order_number or order.name) if order is not None else None


class CustomerShipmentSerializer(SecureModelMixin):
    """A shipment to a customer. Created by the `ship` action, never by plain CRUD;
    the paperwork fields (carrier, tracking, reference, expected delivery, notes) stay
    editable afterwards, since tracking numbers often arrive after the truck leaves."""

    customer_name = serializers.CharField(source='customer.name', read_only=True)
    requires_coc = serializers.BooleanField(source='customer.requires_coc_on_shipment', read_only=True)
    shipped_by_name = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    # For a voided shipment: the units it had, so the record still says what was on it.
    parts = serializers.SerializerMethodField()

    class Meta:
        model = CustomerShipment
        fields = (
            'id', 'shipment_number', 'customer', 'customer_name', 'requires_coc',
            'shipped_at', 'shipped_by', 'shipped_by_name',
            'carrier', 'tracking_number', 'reference', 'expected_delivery', 'notes',
            'quantity', 'parts',
            'is_voided', 'voided_at', 'void_reason',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = (
            'shipment_number', 'customer', 'shipped_at', 'shipped_by',
            'is_voided', 'voided_at', 'void_reason', 'created_at', 'updated_at',
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_shipped_by_name(self, obj):
        u = obj.shipped_by
        if u is None:
            return None
        return (u.get_full_name() or '').strip() or u.email

    @extend_schema_field(serializers.IntegerField())
    def get_quantity(self, obj):
        return obj.parts.count()

    @extend_schema_field(ShipmentPartSerializer(many=True))
    def get_parts(self, obj):
        from Tracker.services.mes.shipping import shipment_units
        return ShipmentPartSerializer(shipment_units(obj), many=True).data


class ReadyPartSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    erp_id = serializers.CharField()
    part_type = serializers.CharField(allow_null=True)
    work_order = serializers.CharField(allow_null=True)
    order_line = serializers.IntegerField(allow_null=True)
    due_date = serializers.DateField(allow_null=True)
    source = serializers.ChoiceField(choices=[('SHIP_STEP', 'At the Ship step'), ('STOCK', 'From stock')])
    status = serializers.CharField()


class ReadyToShipOrderSerializer(serializers.Serializer):
    """Parts that can ship now, for one order (one customer)."""
    order_id = serializers.UUIDField(allow_null=True)
    order_number = serializers.CharField(allow_null=True)
    customer_id = serializers.UUIDField(allow_null=True)
    customer_name = serializers.CharField(allow_null=True)
    requires_coc = serializers.BooleanField()
    parts = ReadyPartSerializer(many=True)


class ShipRequestSerializer(serializers.Serializer):
    part_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    customer = serializers.UUIDField(required=False, allow_null=True)
    carrier = serializers.CharField(required=False, allow_blank=True, default='')
    tracking_number = serializers.CharField(required=False, allow_blank=True, default='')
    reference = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    expected_delivery = serializers.DateField(required=False, allow_null=True)


class VoidShipmentRequestSerializer(serializers.Serializer):
    reason = serializers.CharField()


class LineShipmentSerializer(serializers.Serializer):
    shipment_id = serializers.UUIDField()
    shipment_number = serializers.CharField()
    shipped_at = serializers.DateTimeField()
    quantity = serializers.IntegerField()
    on_time = serializers.BooleanField()


class OrderLineShippingSerializer(serializers.Serializer):
    line_id = serializers.UUIDField()
    line_number = serializers.IntegerField()
    part_type = serializers.CharField()
    ordered = serializers.IntegerField()
    shipped = serializers.IntegerField()
    due_date = serializers.DateField(allow_null=True)
    state = serializers.ChoiceField(choices=[('OPEN', 'Open'), ('PART_SHIPPED', 'Part shipped'),
                                             ('SHIPPED', 'Shipped')])
    shipments = LineShipmentSerializer(many=True)


class OrderShippingSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    lines = OrderLineShippingSerializer(many=True)


class DeliveryPerformanceSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    deliveries = serializers.IntegerField()
    on_time = serializers.IntegerField()
    on_time_pct = serializers.FloatField(allow_null=True)
