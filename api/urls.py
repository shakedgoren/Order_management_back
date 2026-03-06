from django.urls import path
from . import views
from .events import sse_view

urlpatterns = [
    # Shabbat
    path('shabbat/', views.shabbat_list, name='shabbat-list'),
    path('shabbat/current/', views.shabbat_current, name='shabbat-current'),
    path('shabbat/<int:shabbat_id>/', views.shabbat_detail, name='shabbat-detail'),
    path('shabbat/<int:shabbat_id>/close/', views.shabbat_close, name='shabbat-close'),
    path('shabbat/<int:shabbat_id>/inventory/', views.shabbat_update_inventory, name='shabbat-inventory'),

    # Orders
    path('orders/', views.order_create, name='order-create'),
    path('orders/<int:shabbat_id>/by-shabbat/', views.orders_by_shabbat, name='orders-by-shabbat'),
    path('orders/<int:order_id>/', views.order_update, name='order-update'),
    path('orders/<int:order_id>/status/', views.order_update_status, name='order-status'),
    path('orders/<int:order_id>/delete/', views.order_delete, name='order-delete'),
    path('orders/events/', sse_view, name='sse-events'),

    # Customers
    path('customers/', views.customer_list, name='customer-list'),
    path('customers/by-phone/<str:phone>/', views.customer_by_phone, name='customer-by-phone'),
    path('customers/<int:customer_id>/', views.customer_update, name='customer-update'),
]
