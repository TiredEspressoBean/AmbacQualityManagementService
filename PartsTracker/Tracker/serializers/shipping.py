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


class ShipmentLotSerializer(serializers.Serializer):
    """A material lot on a shipment, and how much of it went."""
    id = serializers.UUIDField()
    lot_number = serializers.CharField()
    item_name = serializers.CharField(allow_blank=True)
    quantity = serializers.FloatField()
    unit_of_measure = serializers.CharField(allow_blank=True)


def _lot_rows(lots):
    return [{"id": l.id, "lot_number": l.lot_number, "item_name": l.item_name or "",
             "quantity": float(l.quantity), "unit_of_measure": l.unit_of_measure} for l in lots]


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
    lots = serializers.SerializerMethodField()

    class Meta:
        model = CustomerShipment
        fields = (
            'id', 'shipment_number', 'customer', 'customer_name', 'requires_coc',
            'shipped_at', 'shipped_by', 'shipped_by_name',
            'carrier', 'tracking_number', 'reference', 'expected_delivery', 'notes',
            'quantity', 'parts', 'lots',
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

    @extend_schema_field(ShipmentLotSerializer(many=True))
    def get_lots(self, obj):
        from Tracker.services.mes.shipping import shipment_lots
        return ShipmentLotSerializer(_lot_rows(shipment_lots(obj)), many=True).data

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


class ReadyLotSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    lot_number = serializers.CharField()
    item_name = serializers.CharField(allow_blank=True)
    quantity_remaining = serializers.FloatField()
    unit_of_measure = serializers.CharField(allow_blank=True)
    storage_location = serializers.CharField(allow_blank=True)


class ReadyToShipOrderSerializer(serializers.Serializer):
    """Parts that can ship now, for one order (one customer)."""
    order_id = serializers.UUIDField(allow_null=True)
    order_number = serializers.CharField(allow_null=True)
    customer_id = serializers.UUIDField(allow_null=True)
    customer_name = serializers.CharField(allow_null=True)
    requires_coc = serializers.BooleanField()
    parts = ReadyPartSerializer(many=True)
    # A customer's own material still here, to send back to them.
    lots = ReadyLotSerializer(many=True)


class ShipLotRequestSerializer(serializers.Serializer):
    lot_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True,
                                        help_text="Ship only this much (split off first). Omit for all of it.")


class ShipRequestSerializer(serializers.Serializer):
    part_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    lots = ShipLotRequestSerializer(many=True, required=False, default=list)
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
