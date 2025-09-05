from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Management panel URLs
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/orders/', views.management_order_list, name='management_order_list'),
    path('management/orders/<int:order_id>/', views.management_order_detail, name='management_order_detail'),
    path('management/orders/<int:order_id>/edit/', views.management_order_edit, name='management_order_edit'),
    path('management/orders/<int:order_id>/status/', views.management_order_update_status, name='management_order_update_status'),
    path('management/payments/', views.management_payment_list, name='management_payment_list'),
    path('management/payments/<int:payment_id>/', views.management_payment_detail, name='management_payment_detail'),
    path('management/payments/add/<int:order_id>/', views.management_payment_add, name='management_payment_add'),
    path('management/quick-order/', views.management_quick_order, name='management_quick_order'),
] 