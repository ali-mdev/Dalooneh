from django.db import models
import uuid
import datetime
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
import os

# Try to import qrcode but make it optional
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

# Create your models here.

class Table(models.Model):
    """Model for restaurant tables"""
    number = models.IntegerField(unique=True)
    seats = models.IntegerField(default=4)
    is_active = models.BooleanField(default=True)
    qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Table {self.number}'
    
    def generate_qr_code(self):
        """Generate QR code for table access - only generates if no QR code exists yet"""
        # If QR code already exists, don't regenerate it
        if self.qr_code:
            return self.qr_code.url
            
        if not QRCODE_AVAILABLE:
            return None
            
        # Create a professional looking QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction for better readability
            box_size=12,  # Bigger box size for clearer image
            border=4,
        )
        
        # Generate access URL with table number - use a relative URL instead of settings.SITE_URL
        access_url = f"/tables/access/{self.number}/"
        qr.add_data(access_url)
        qr.make(fit=True)
        
        # Create QR code image with better styling
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to media directory
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'table_{self.number}_permanent_qr.png'
        
        # Save QR code with permanent name
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        self.save()
        
        return self.qr_code.url
    
    def get_access_url(self):
        """Get URL for table access"""
        return f"/tables/access/{self.number}/"
    
    def get_active_session(self):
        """Get active session for table"""
        return self.sessions.filter(is_active=True).first()
    
    def get_or_create_active_session(self):
        """Get or create active session for table"""
        session = self.get_active_session()
        if not session:
            session = TableSession.objects.create(table=self)
        return session
    
    @property
    def is_occupied(self):
        """
        Check if table is occupied.
        A table is considered occupied only when it has an active order.
        Just having an active session doesn't mean the table is occupied.
        """
        return self.orders.filter(status__in=['pending', 'confirmed', 'preparing', 'ready']).exists()
    
    def free_table(self):
        """
        Free the table by deactivating any active sessions and cancelling all active orders
        """
        # First deactivate any active session
        active_session = self.get_active_session()
        if active_session:
            active_session.deactivate()
            
        # Then cancel all active orders for this table (important for orders in confirmed/preparing/ready status)
        from orders.models import Order
        active_orders = Order.objects.filter(
            table=self,
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        )
        
        for order in active_orders:
            order.status = 'cancelled'
            order.save(update_fields=['status'])
            print(f"DEBUG: Cancelled order {order.id} for table {self.number}")
    
    @property
    def current_order(self):
        """Get current order for table"""
        return self.orders.filter(status__in=['pending', 'confirmed', 'preparing', 'ready']).first()
    
    @property
    def last_order_time(self):
        """Get last order time"""
        last_order = self.orders.order_by('-created_at').first()
        return last_order.created_at if last_order else None


class TableSession(models.Model):
    """Model for secure table sessions with tokens for QR codes"""
    table = models.ForeignKey(
        Table, 
        on_delete=models.CASCADE, 
        related_name="sessions", 
        verbose_name="Table"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Creation Time"
    )
    expires_at = models.DateTimeField(
        verbose_name="Expiration Time"
    )
    last_used = models.DateTimeField(
        auto_now=True, 
        verbose_name="Last Used"
    )
    order_submitted = models.BooleanField(
        default=False,
        verbose_name="Order Submitted"
    )
    
    class Meta:
        verbose_name = "Table Session"
        verbose_name_plural = "Table Sessions"
    
    def __str__(self):
        return f"Table {self.table.number} Session"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiration time (12 minutes from creation)
            self.expires_at = timezone.now() + timezone.timedelta(minutes=12)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if session is expired"""
        is_expired = timezone.now() > self.expires_at
        
        # If expired and still active, deactivate it and clean up cart items
        if is_expired and self.is_active:
            self.deactivate()
            
        return is_expired
    
    def is_valid(self):
        """Check if session is valid"""
        return self.is_active and not self.is_expired()
    
    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
    
    def deactivate(self):
        """Deactivate session"""
        print(f"DEBUG: Deactivating session {self.token} for table {self.table.number}")
        self.is_active = False
        self.save(update_fields=['is_active'])
        
        # Clear any cart items for this table's pending orders
        from orders.models import Order
        pending_orders = Order.objects.filter(
            table=self.table,
            status='pending'
        )
        
        # Cancel pending orders to properly free the table
        for order in pending_orders:
            if order.status == 'pending':
                order.status = 'cancelled'
                order.save(update_fields=['status'])
        
        if pending_orders.exists():
            print(f"DEBUG: Cleaning up {pending_orders.count()} pending orders for table {self.table.number}")
            for order in pending_orders:
                # Delete all order items
                item_count = order.items.count()
                if item_count > 0:
                    print(f"DEBUG: Deleting {item_count} items from order {order.id}")
                    order.items.all().delete()
                # Update order totals
                order.total_amount = 0
                order.final_amount = 0
                order.save(update_fields=['total_amount', 'final_amount'])
                print(f"DEBUG: Reset order {order.id} totals to 0")
        else:
            print(f"DEBUG: No pending orders found for table {self.table.number}")
    
    def mark_order_submitted(self):
        """Mark that an order has been submitted for this session"""
        self.order_submitted = True
        self.save(update_fields=['order_submitted'])
