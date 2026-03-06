from rest_framework import serializers
from .models import Shabbat, Inventory, Customer, Order, OrderItem


# -------- Inventory --------
class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['id', 'shabbat_id', 'location', 'jachnun', 'jachnun_butter',
                  'kubane', 'burekas_cheese', 'burekas_potato', 'burekas_spinach',
                  'malabi', 'orange_juice']
        read_only_fields = ['id']


class InventoryInputSerializer(serializers.Serializer):
    location = serializers.ChoiceField(choices=Inventory.LOCATION_CHOICES)
    jachnun = serializers.IntegerField(default=0, required=False)
    jachnun_butter = serializers.IntegerField(default=0, required=False)
    kubane = serializers.IntegerField(default=0, required=False)
    burekas_cheese = serializers.IntegerField(default=0, required=False)
    burekas_potato = serializers.IntegerField(default=0, required=False)
    burekas_spinach = serializers.IntegerField(default=0, required=False)
    malabi = serializers.IntegerField(default=0, required=False)
    orange_juice = serializers.IntegerField(default=0, required=False)


# -------- Customer --------
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'address']
        read_only_fields = ['id']


# -------- Order Items --------
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'item_name', 'quantity']
        read_only_fields = ['id']


class OrderItemInputSerializer(serializers.Serializer):
    item_name = serializers.CharField()
    quantity = serializers.IntegerField()


# -------- Order --------
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'shabbat_id', 'customer_id', 'is_walk_in', 'location',
                  'order_type', 'delivery_time', 'delivery_address', 'status',
                  'payment_type', 'notes', 'total_price', 'created_at',
                  'items', 'customer']
        read_only_fields = ['id', 'created_at']


class OrderCreateSerializer(serializers.Serializer):
    shabbat_id = serializers.IntegerField()
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    is_walk_in = serializers.BooleanField(default=False)
    location = serializers.ChoiceField(choices=Order.LOCATION_CHOICES)
    order_type = serializers.ChoiceField(choices=Order.TYPE_CHOICES, default='pickup')
    delivery_time = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    delivery_address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_type = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES, default='none')
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    items = OrderItemInputSerializer(many=True, default=[])
    # Inline customer creation
    customer_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer_address = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class OrderUpdateSerializer(serializers.Serializer):
    delivery_time = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    delivery_address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_type = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES, required=False)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    items = OrderItemInputSerializer(many=True, required=False)


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)


# -------- Shabbat --------
class ShabbatSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(many=True, read_only=True)

    class Meta:
        model = Shabbat
        fields = ['id', 'date', 'is_open', 'yavne_open', 'ayyanot_open',
                  'has_delivery', 'employees', 'created_at', 'inventory']
        read_only_fields = ['id', 'created_at']


class ShabbatDetailSerializer(ShabbatSerializer):
    orders = OrderSerializer(many=True, read_only=True)

    class Meta(ShabbatSerializer.Meta):
        fields = ShabbatSerializer.Meta.fields + ['orders']


class ShabbatCreateSerializer(serializers.Serializer):
    date = serializers.CharField()
    yavne_open = serializers.BooleanField(default=False)
    ayyanot_open = serializers.BooleanField(default=False)
    has_delivery = serializers.BooleanField(default=False)
    employees = serializers.ListField(child=serializers.CharField(), default=[])
    yavne_inventory = InventoryInputSerializer(required=False, allow_null=True)
    ayyanot_inventory = InventoryInputSerializer(required=False, allow_null=True)
