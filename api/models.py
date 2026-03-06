from django.db import models
import json


class LegacyJSONField(models.JSONField):
    """Handle PostgreSQL json (not jsonb) columns where data may arrive already parsed."""
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value


class Shabbat(models.Model):
    date = models.CharField(max_length=100)
    is_open = models.BooleanField(default=True)
    yavne_open = models.BooleanField(default=False)
    ayyanot_open = models.BooleanField(default=False)
    has_delivery = models.BooleanField(default=False)
    employees = LegacyJSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shabbats'
        ordering = ['-created_at']

    def __str__(self):
        return f"Shabbat {self.date}"


class Inventory(models.Model):
    LOCATION_CHOICES = [('yavne', 'Yavne'), ('ayyanot', 'Ayyanot')]

    shabbat = models.ForeignKey(Shabbat, on_delete=models.CASCADE, related_name='inventory')
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    jachnun = models.IntegerField(default=0)
    jachnun_butter = models.IntegerField(default=0)
    kubane = models.IntegerField(default=0)
    burekas_cheese = models.IntegerField(default=0)
    burekas_potato = models.IntegerField(default=0)
    burekas_spinach = models.IntegerField(default=0)
    malabi = models.IntegerField(default=0)
    orange_juice = models.IntegerField(default=0)

    class Meta:
        db_table = 'inventory'

    def __str__(self):
        return f"Inventory {self.location} for Shabbat {self.shabbat_id}"


class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'customers'

    def __str__(self):
        return self.name


class Order(models.Model):
    LOCATION_CHOICES = [('yavne', 'Yavne'), ('ayyanot', 'Ayyanot')]
    TYPE_CHOICES = [('pickup', 'Pickup'), ('delivery', 'Delivery')]
    STATUS_CHOICES = [('waiting', 'Waiting'), ('done', 'Done')]
    PAYMENT_CHOICES = [
        ('bit', 'Bit'), ('paybox', 'Paybox'), ('cash', 'Cash'),
        ('credit', 'Credit'), ('none', 'None'),
    ]

    shabbat = models.ForeignKey(Shabbat, on_delete=models.CASCADE, related_name='orders')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    is_walk_in = models.BooleanField(default=False)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    order_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='pickup')
    delivery_time = models.CharField(max_length=20, blank=True, null=True)
    delivery_address = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='none')
    notes = models.TextField(blank=True, null=True)
    total_price = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
        ordering = ['created_at']

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"
