from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

class Notification(models.Model):
    """Model for storing notifications"""
    NOTIFICATION_TYPES = [
        ('new_order', 'New Order'),
        ('order_status', 'Order Status Change'),
        ('payment', 'Payment'),
        ('system', 'System'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='Recipient')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='Notification Type')
    title = models.CharField(max_length=255, verbose_name='Title')
    message = models.TextField(verbose_name='Message')
    read = models.BooleanField(default=False, verbose_name='Read')
    
    # Link to related object (e.g., order)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional fields for storing notification-related data
    data = models.JSONField(default=dict, blank=True, verbose_name='Data')
    url = models.CharField(max_length=255, blank=True, verbose_name='Link')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title 