from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('', views.management_index, name='management_index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('products/', views.product_management, name='product_management'),
    path('categories/', views.category_management, name='category_management'),
    path('reports/', views.reports, name='reports'),
] 