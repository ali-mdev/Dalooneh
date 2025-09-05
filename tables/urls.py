from django.urls import path
from . import views

app_name = 'tables'

urlpatterns = [
    # Table access and QR code
    path('access/<int:table_number>/', views.table_access, name='table_access'),
    path('validate/<str:token>/', views.validate_token, name='validate_token'),
    path('check-session/', views.check_session, name='check_session'),
    path('generate-qr/<int:table_id>/', views.generate_qr_data, name='generate_qr'),
    path('status/<int:table_id>/', views.table_status, name='table_status'),
    
    # Cart and order management
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('update-cart-item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove-cart-item/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('get-cart-count/', views.get_cart_count_ajax, name='get_cart_count'),
    path('submit-order/', views.submit_order, name='submit_order'),
    path('complete-order/<int:order_id>/', views.complete_order, name='complete_order'),
    path('order-summary/', views.order_summary, name='order_summary'),
    path('order-summary/<int:order_id>/', views.order_summary, name='order_summary_with_id'),
    
    # Test and development
    path('test-qr/', views.create_test_qr, name='test_qr'),
    
    # Management panel URLs
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/tables/', views.management_table_list, name='management_table_list'),
    path('management/tables/add/', views.management_table_add, name='management_table_add'),
    path('management/tables/<int:table_id>/', views.management_table_detail, name='management_table_detail'),
    path('management/tables/<int:table_id>/edit/', views.management_table_edit, name='management_table_edit'),
    path('management/tables/<int:table_id>/delete/', views.management_table_delete, name='management_table_delete'),
    path('management/tables/<int:table_id>/toggle-status/', views.management_table_toggle_status, name='management_table_toggle_status'),
    path('management/tables/<int:table_id>/free/', views.management_table_free, name='management_table_free'),
    path('management/tables/free-all/', views.management_free_all_tables, name='management_free_all_tables'),
    path('management/generate-qr/', views.management_generate_qr, name='management_generate_qr'),
    path('management/generate-all-qr/', views.management_generate_all_qr, name='management_generate_all_qr'),
    path('management/sessions/', views.management_session_list, name='management_session_list'),
    path('management/sessions/<int:session_id>/', views.management_session_detail, name='management_session_detail'),
    path('management/sessions/deactivate/', views.management_session_deactivate, name='management_session_deactivate'),
] 