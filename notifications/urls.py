from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('test-notification/', views.test_notification, name='test_notification'),
    path('trigger-new-order/', views.trigger_new_order, name='trigger_new_order'),
    path('get-notifications/', views.get_notifications, name='get_notifications'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
] 