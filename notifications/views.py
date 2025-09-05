import json
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from orders.models import Order
from .models import Notification

channel_layer = get_channel_layer()

@user_passes_test(lambda u: u.is_staff)
def test_notification(request):
    """
    Test endpoint for sending a test order notification
    """
    # Create test notification message
    notification_message = {
        'type': 'new_order',
        'order_id': 999999,
        'table': 'Test',
        'customer': 'Test User',
        'total_price': 125000,
        'items_count': 3,
        'timestamp': '2023-06-15T14:30:00Z',
        'order_url': '/orders/management/order/test/',
    }
    
    # Send message to WebSocket channel
    async_to_sync(channel_layer.group_send)(
        "restaurant_managers",
        {
            'type': 'notification_message',
            'message': notification_message
        }
    )
    
    # Save test notification to database
    Notification.objects.create(
        recipient=request.user,
        notification_type='new_order',
        title='New Test Order',
        message=f'This is a test notification for a new order',
        data=notification_message,
        url=notification_message['order_url']
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Test notification sent successfully.'
    })

@require_http_methods(["POST"])
def trigger_new_order(request):
    """
    API for sending new order notification
    """
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        table_number = data.get('table_number', 'Unknown')
        customer_name = data.get('customer_name', 'Guest')
        total_price = data.get('total_price', 0)
        items_count = data.get('items_count', 0)
        
        # Create notification message
        notification_message = {
            'type': 'new_order',
            'order_id': order_id,
            'table': str(table_number),
            'customer': str(customer_name),
            'total_price': float(total_price),
            'items_count': items_count,
            'timestamp': '',  # Current time
            'order_url': f"/orders/management/order/{order_id}/",
            'is_modal': True,  # This notification should be displayed as modal
        }
        
        # Send message to WebSocket channel
        async_to_sync(channel_layer.group_send)(
            "restaurant_managers",
            {
                'type': 'notification_message',
                'message': notification_message
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Notification sent successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error sending notification: {str(e)}'
        }, status=400)

@user_passes_test(lambda u: u.is_staff)
def get_notifications(request):
    """
    Get user notification list
    """
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    
    notifications_list = []
    for notification in notifications:
        notifications_list.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'url': notification.url,
            'read': notification.read,
            'data': notification.data,
            'timestamp': notification.created_at.isoformat()
        })
    
    return JsonResponse({
        'success': True,
        'notifications': notifications_list
    })

@user_passes_test(lambda u: u.is_staff)
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.read = True
    notification.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Notification marked as read.'
    })

@user_passes_test(lambda u: u.is_staff)
def mark_all_notifications_read(request):
    """
    Mark all notifications as read
    """
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    
    return JsonResponse({
        'success': True,
        'message': 'All notifications marked as read.'
    }) 