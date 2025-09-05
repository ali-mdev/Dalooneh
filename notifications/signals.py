import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from orders.models import Order
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from notifications.models import Notification
import logging

# Configure logger for debugging
logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

@receiver(post_save, sender=Order)
def send_order_notification(sender, instance, created, **kwargs):
    """
    Send notification for confirmed orders only
    """
    logger.debug(f"Signal triggered for Order ID: {instance.id}, created: {created}, status: {instance.status}")
    
    # Send order notification only for confirmed orders
    if instance.status == 'confirmed':
        try:
            table_number = instance.table.number if instance.table else "Online Order"
            customer_name = instance.customer.user.get_full_name() if instance.customer and hasattr(instance.customer, 'user') and instance.customer.user else "Guest"
            
            # Create notification message
            notification_message = {
                'type': 'new_order',
                'order_id': instance.id,
                'table': str(table_number),
                'customer': str(customer_name),
                'total_price': float(instance.total_amount),
                'items_count': instance.items.count(),
                'timestamp': instance.created_at.isoformat(),
                'order_url': f"/orders/management/orders/{instance.id}/",
                'is_modal': True,  # Display as modal
            }
            
            # Save notification to database only for super users (not all staff)
            content_type = ContentType.objects.get_for_model(Order)
            superusers = User.objects.filter(is_superuser=True, is_active=True)
            
            for user in superusers:
                Notification.objects.create(
                    recipient=user,
                    notification_type='new_order',
                    title='Order Confirmed',
                    message=f'Order from table {table_number} by {customer_name} has been confirmed',
                    content_type=content_type,
                    object_id=instance.id,
                    data=notification_message,
                    url=notification_message['order_url']
                )
            
            logger.debug(f"Sending notification for Order: {notification_message}")
            
            # Send message to WebSocket channel only for senior managers
            async_to_sync(channel_layer.group_send)(
                "restaurant_managers",
                {
                    'type': 'notification_message',
                    'message': notification_message
                }
            )
            logger.debug("Notification sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}", exc_info=True) 