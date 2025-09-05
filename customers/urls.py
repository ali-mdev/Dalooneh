from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile, name='profile'),
    path('orders/', views.order_history, name='order_history'),
    path('discounts/', views.discount_list, name='discount_list'),
    path('submit-phone/', views.submit_phone_number, name='submit_phone_number'),
    
    # Management panel URLs
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/customers/', views.management_customer_list, name='management_customer_list'),
    path('management/customers/add/', views.management_customer_add, name='management_customer_add'),
    path('management/customers/<int:customer_id>/', views.management_customer_detail, name='management_customer_detail'),
    path('management/customers/<int:customer_id>/edit/', views.management_customer_edit, name='management_customer_edit'),
    path('management/ratings/', views.management_rating_list, name='management_rating_list'),
    path('management/discounts/', views.management_discount_list, name='management_discount_list'),
    path('management/discounts/add/', views.management_discount_add, name='management_discount_add'),
    path('management/discounts/<int:discount_id>/edit/', views.management_discount_edit, name='management_discount_edit'),
    path('management/discounts/<int:discount_id>/delete/', views.management_discount_delete, name='management_discount_delete'),
] 