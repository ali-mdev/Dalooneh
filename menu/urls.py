from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.MenuView.as_view(), name='menu'),
    path('category/', views.public_category_list, name='public_category_list'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    # path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Management panel URLs
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/categories/', views.management_category_list, name='management_category_list'),
    path('management/categories/add/', views.management_category_add, name='management_category_add'),
    path('management/categories/<int:category_id>/edit/', views.management_category_edit, name='management_category_edit'),
    path('management/categories/<int:category_id>/delete/', views.management_category_delete, name='management_category_delete'),
    path('management/products/', views.management_product_list, name='management_product_list'),
    path('management/products/add/', views.management_product_add, name='management_product_add'),
    path('management/products/<int:product_id>/edit/', views.management_product_edit, name='management_product_edit'),
    path('management/products/<int:product_id>/delete/', views.management_product_delete, name='management_product_delete'),
    # New URLs for toggling product status and availability
    path('management/products/<int:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
    path('management/products/<int:product_id>/toggle-availability/', views.toggle_product_availability, name='toggle_product_availability'),
] 