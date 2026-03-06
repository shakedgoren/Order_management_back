from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from .models import Shabbat, Inventory, Customer, Order, OrderItem
from .serializers import (
    ShabbatSerializer, ShabbatDetailSerializer, ShabbatCreateSerializer,
    InventorySerializer, InventoryInputSerializer,
    CustomerSerializer,
    OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer, OrderStatusUpdateSerializer,
)
from .events import broadcast_event

# ===== Price Calculation =====
ITEM_PRICES = {
    "ג'חנון": 22,
    "ג'חנון חמאה": 25,
    "תוספת ביצה": 3,
    "תוספת רסק": 3,
    "קובנה": 25,
    "בורקס גבינה": 27,
    'בורקס תפו"א': 27,
    "בורקס תרד וגבינה": 27,
    "זיווה": 30,
    "מלוואח": 30,
    "מלוואח ממולא": 30,
    "מלוואח מגולגל": 30,
    "פתות": 35,
    "לאבנה": 35,
    "מלבי": 12,
    "מיץ תפוזים": 25,
    "מיץ רימונים": 25,
    "עוגת שמרים": 45,
    "מאפים": 34,
}

ITEM_NAME_TO_COLUMN = {
    "ג'חנון": "jachnun",
    "ג'חנון חמאה": "jachnun_butter",
    "קובנה": "kubane",
    "בורקס גבינה": "burekas_cheese",
    'בורקס תפו"א': "burekas_potato",
    "בורקס תרד וגבינה": "burekas_spinach",
    "מלבי": "malabi",
    "מיץ תפוזים": "orange_juice",
}


def calculate_total_price(items):
    total = 0
    for item in items:
        price = ITEM_PRICES.get(item.get('item_name', ''), 0)
        total += price * (item.get('quantity', 0) or 0)
    return total


def check_inventory_availability(shabbat_id, location, items):
    """Check if inventory has enough stock for the requested items. Returns error message or None."""
    inv_location = 'yavne' if location == 'yavne' else 'ayyanot'
    try:
        inv = Inventory.objects.get(shabbat_id=shabbat_id, location=inv_location)
    except Inventory.DoesNotExist:
        return None  # No inventory tracking — allow order

    for item in items:
        item_name = item.get('item_name', '') if isinstance(item, dict) else item.item_name
        quantity = item.get('quantity', 0) if isinstance(item, dict) else item.quantity
        col = ITEM_NAME_TO_COLUMN.get(item_name)
        if col and hasattr(inv, col):
            available = getattr(inv, col) or 0
            if available <= 0 and quantity > 0:
                return f'{item_name} אזל מהמלאי'
            if quantity > available:
                return f'אין מספיק {item_name} במלאי (נשאר: {available})'
    return None


def deduct_inventory(shabbat_id, location, items, reverse=False):
    """Deduct or restore inventory for ordered items."""
    inv_location = 'yavne' if location == 'yavne' else 'ayyanot'
    try:
        inv = Inventory.objects.get(shabbat_id=shabbat_id, location=inv_location)
    except Inventory.DoesNotExist:
        return

    for item in items:
        item_name = item.get('item_name', '') if isinstance(item, dict) else item.item_name
        quantity = item.get('quantity', 0) if isinstance(item, dict) else item.quantity
        col = ITEM_NAME_TO_COLUMN.get(item_name)
        if col and hasattr(inv, col):
            current = getattr(inv, col) or 0
            delta = -quantity if not reverse else quantity
            setattr(inv, col, max(0, current + delta))
    inv.save()


# ===== Shabbat Views =====
@api_view(['GET', 'POST'])
def shabbat_list(request):
    if request.method == 'GET':
        shabbats = Shabbat.objects.prefetch_related('inventory').all()
        serializer = ShabbatSerializer(shabbats, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        ser = ShabbatCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Check if already open
        if Shabbat.objects.filter(is_open=True).exists():
            return Response({'detail': 'יש כבר שבת פתוחה'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            shabbat = Shabbat.objects.create(
                date=data['date'],
                yavne_open=data.get('yavne_open', False),
                ayyanot_open=data.get('ayyanot_open', False),
                has_delivery=data.get('has_delivery', False),
                employees=data.get('employees', []),
            )

            if data.get('yavne_open') and data.get('yavne_inventory'):
                inv_data = data['yavne_inventory']
                Inventory.objects.create(
                    shabbat=shabbat, location='yavne',
                    **{k: inv_data.get(k, 0) for k in ['jachnun', 'jachnun_butter', 'kubane',
                        'burekas_cheese', 'burekas_potato', 'burekas_spinach', 'malabi', 'orange_juice']}
                )

            if data.get('ayyanot_open') and data.get('ayyanot_inventory'):
                inv_data = data['ayyanot_inventory']
                Inventory.objects.create(
                    shabbat=shabbat, location='ayyanot',
                    **{k: inv_data.get(k, 0) for k in ['jachnun', 'jachnun_butter', 'kubane',
                        'burekas_cheese', 'burekas_potato', 'burekas_spinach', 'malabi', 'orange_juice']}
                )

        shabbat.refresh_from_db()
        broadcast_event({"type": "shabbat_opened", "shabbat_id": shabbat.id})
        serializer = ShabbatSerializer(Shabbat.objects.prefetch_related('inventory').get(id=shabbat.id))
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def shabbat_current(request):
    try:
        shabbat = Shabbat.objects.prefetch_related('inventory').get(is_open=True)
    except Shabbat.DoesNotExist:
        return Response({'detail': 'אין שבת פתוחה כרגע'}, status=status.HTTP_404_NOT_FOUND)
    serializer = ShabbatSerializer(shabbat)
    return Response(serializer.data)


@api_view(['GET'])
def shabbat_detail(request, shabbat_id):
    try:
        shabbat = Shabbat.objects.prefetch_related(
            'inventory', 'orders__items', 'orders__customer'
        ).get(id=shabbat_id)
    except Shabbat.DoesNotExist:
        return Response({'detail': 'שבת לא נמצאה'}, status=status.HTTP_404_NOT_FOUND)
    serializer = ShabbatDetailSerializer(shabbat)
    return Response(serializer.data)


@api_view(['PUT'])
def shabbat_close(request, shabbat_id):
    try:
        shabbat = Shabbat.objects.get(id=shabbat_id)
    except Shabbat.DoesNotExist:
        return Response({'detail': 'שבת לא נמצאה'}, status=status.HTTP_404_NOT_FOUND)
    shabbat.is_open = False
    shabbat.save()
    broadcast_event({"type": "shabbat_closed", "shabbat_id": shabbat_id})
    return Response({"message": "השבת נסגרה"})


@api_view(['GET'])
def shabbat_inventory(request, shabbat_id):
    inventories = Inventory.objects.filter(shabbat_id=shabbat_id)
    serializer = InventorySerializer(inventories, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
def shabbat_update_inventory(request, shabbat_id):
    items = request.data if isinstance(request.data, list) else [request.data]
    for inv_data in items:
        ser = InventoryInputSerializer(data=inv_data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            inv = Inventory.objects.get(shabbat_id=shabbat_id, location=d['location'])
            for field in ['jachnun', 'jachnun_butter', 'kubane', 'burekas_cheese',
                          'burekas_potato', 'burekas_spinach', 'malabi', 'orange_juice']:
                if field in d:
                    setattr(inv, field, d[field])
            inv.save()
        except Inventory.DoesNotExist:
            pass
    broadcast_event({"type": "inventory_updated", "shabbat_id": shabbat_id})
    return Response({"message": "מלאי עודכן בהצלחה"})


# ===== Order Views =====
@api_view(['POST'])
def order_create(request):
    ser = OrderCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    customer_id = data.get('customer_id')

    with transaction.atomic():
        if not data.get('is_walk_in'):
            if not customer_id and data.get('customer_phone'):
                try:
                    existing = Customer.objects.get(phone=data['customer_phone'])
                    customer_id = existing.id
                    if data.get('order_type') == 'delivery' and data.get('delivery_address'):
                        existing.address = data['delivery_address']
                        existing.save()
                except Customer.DoesNotExist:
                    new_customer = Customer.objects.create(
                        name=data.get('customer_name', ''),
                        phone=data['customer_phone'],
                        address=data.get('delivery_address') if data.get('order_type') == 'delivery' else None,
                    )
                    customer_id = new_customer.id
            elif customer_id and data.get('order_type') == 'delivery' and data.get('delivery_address'):
                try:
                    cust = Customer.objects.get(id=customer_id)
                    cust.address = data['delivery_address']
                    cust.save()
                except Customer.DoesNotExist:
                    pass

        # Check inventory availability before creating order
        order_items = data.get('items', [])
        if order_items and not data.get('is_walk_in'):
            err = check_inventory_availability(data['shabbat_id'], data['location'], order_items)
            if err:
                return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            shabbat_id=data['shabbat_id'],
            customer_id=customer_id,
            is_walk_in=data.get('is_walk_in', False),
            location=data['location'],
            order_type=data.get('order_type', 'pickup'),
            delivery_time=data.get('delivery_time'),
            delivery_address=data.get('delivery_address'),
            payment_type=data.get('payment_type', 'none'),
            notes=data.get('notes'),
            total_price=calculate_total_price(data.get('items', [])),
        )

        for item in data.get('items', []):
            if item.get('quantity', 0) > 0:
                OrderItem.objects.create(
                    order=order,
                    item_name=item['item_name'],
                    quantity=item['quantity'],
                )

        deduct_inventory(data['shabbat_id'], data['location'], data.get('items', []))

    order = Order.objects.select_related('customer').prefetch_related('items').get(id=order.id)
    broadcast_event({"type": "order_created", "shabbat_id": data['shabbat_id'], "order_id": order.id})
    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def orders_by_shabbat(request, shabbat_id):
    orders = Order.objects.filter(shabbat_id=shabbat_id).select_related('customer').prefetch_related('items')
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['PUT'])
def order_update(request, order_id):
    ser = OrderUpdateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    try:
        order = Order.objects.select_related('customer').prefetch_related('items').get(id=order_id)
    except Order.DoesNotExist:
        return Response({'detail': 'הזמנה לא נמצאה'}, status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        if 'delivery_time' in data and data['delivery_time'] is not None:
            order.delivery_time = data['delivery_time']
        if 'delivery_address' in data and data['delivery_address'] is not None:
            order.delivery_address = data['delivery_address']
        if 'payment_type' in data and data['payment_type'] is not None:
            order.payment_type = data['payment_type']
        if 'notes' in data and data['notes'] is not None:
            order.notes = data['notes']

        if 'items' in data:
            items_data = data['items']

            # Check inventory availability (accounting for current order being returned first)
            if not order.is_walk_in:
                # Temporarily restore old inventory to check against full stock
                old_items = [{'item_name': i.item_name, 'quantity': i.quantity} for i in order.items.all()]
                deduct_inventory(order.shabbat_id, order.location, old_items, reverse=True)
                err = check_inventory_availability(order.shabbat_id, order.location, items_data)
                if err:
                    # Re-deduct old items since we're aborting
                    deduct_inventory(order.shabbat_id, order.location, old_items)
                    return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
                # Re-deduct old items — the code below will handle the full swap
                deduct_inventory(order.shabbat_id, order.location, old_items)

            order.total_price = calculate_total_price(items_data)

            # Restore old inventory
            old_items = [{'item_name': i.item_name, 'quantity': i.quantity} for i in order.items.all()]
            deduct_inventory(order.shabbat_id, order.location, old_items, reverse=True)

            # Delete old items
            order.items.all().delete()

            # Add new items
            for item in items_data:
                if item.get('quantity', 0) > 0:
                    OrderItem.objects.create(order=order, item_name=item['item_name'], quantity=item['quantity'])

            # Deduct new inventory
            deduct_inventory(order.shabbat_id, order.location, items_data)

        order.save()

    order = Order.objects.select_related('customer').prefetch_related('items').get(id=order_id)
    broadcast_event({"type": "order_updated", "shabbat_id": order.shabbat_id, "order_id": order.id})
    return Response(OrderSerializer(order).data)


@api_view(['PUT'])
def order_update_status(request, order_id):
    ser = OrderStatusUpdateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'detail': 'הזמנה לא נמצאה'}, status=status.HTTP_404_NOT_FOUND)

    order.status = ser.validated_data['status']
    order.save()

    order = Order.objects.select_related('customer').prefetch_related('items').get(id=order_id)
    broadcast_event({"type": "order_status_changed", "shabbat_id": order.shabbat_id, "order_id": order.id})
    return Response(OrderSerializer(order).data)


@api_view(['DELETE'])
def order_delete(request, order_id):
    try:
        order = Order.objects.prefetch_related('items').get(id=order_id)
    except Order.DoesNotExist:
        return Response({'detail': 'הזמנה לא נמצאה'}, status=status.HTTP_404_NOT_FOUND)

    old_items = [{'item_name': i.item_name, 'quantity': i.quantity} for i in order.items.all()]
    deduct_inventory(order.shabbat_id, order.location, old_items, reverse=True)
    shabbat_id = order.shabbat_id
    order.delete()
    broadcast_event({"type": "order_deleted", "shabbat_id": shabbat_id, "order_id": order_id})
    return Response({"message": "הזמנה נמחקה"})


# ===== Customer Views =====
@api_view(['GET', 'POST'])
def customer_list(request):
    if request.method == 'GET':
        name = request.query_params.get('name', '')
        if name:
            customers = Customer.objects.filter(name__icontains=name)[:10]
        else:
            customers = Customer.objects.all()[:10]
        return Response(CustomerSerializer(customers, many=True).data)

    elif request.method == 'POST':
        ser = CustomerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if Customer.objects.filter(phone=ser.validated_data['phone']).exists():
            return Response({'detail': 'לקוח עם מספר זה כבר קיים'}, status=status.HTTP_400_BAD_REQUEST)
        customer = ser.save()
        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def customer_by_phone(request, phone):
    try:
        customer = Customer.objects.get(phone=phone)
    except Customer.DoesNotExist:
        return Response({'detail': 'לקוח לא נמצא'}, status=status.HTTP_404_NOT_FOUND)
    return Response(CustomerSerializer(customer).data)


@api_view(['PUT'])
def customer_update(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({'detail': 'לקוח לא נמצא'}, status=status.HTTP_404_NOT_FOUND)
    ser = CustomerSerializer(customer, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
