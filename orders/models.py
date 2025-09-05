from django.db import models, transaction
from django.conf import settings
from menu.models import Product
from customers.models import Customer
from tables.models import Table

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders', verbose_name='Customer')
    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name='orders', verbose_name='Table')
    order_number = models.CharField(max_length=20, unique=True, verbose_name='Order Number')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='Payment Status')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total Amount')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Discount Amount')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Final Amount')
    notes = models.TextField(blank=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            import datetime
            prefix = datetime.datetime.now().strftime('%Y%m%d')
            
            # Use a transaction with select_for_update to prevent race conditions
            with transaction.atomic():
                # Lock the table to prevent concurrent order number generation
                last_order = Order.objects.filter(order_number__startswith=prefix).order_by('-order_number').select_for_update().first()
                
                if last_order:
                    try:
                        last_number = int(last_order.order_number[-4:])
                        new_number = str(last_number + 1).zfill(4)
                    except (ValueError, IndexError):
                        # Fallback if there's an issue with the last order number format
                        new_number = '0001'
                else:
                    new_number = '0001'
                    
                self.order_number = f"{prefix}{new_number}"
        
        super().save(*args, **kwargs)

    @property
    def is_paid(self):
        return self.payment_status == 'paid'

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        paid_amount = sum(payment.amount for payment in self.payments.filter(status='completed'))
        return self.final_amount - paid_amount

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Order')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Product')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Quantity')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Unit Price')
    notes = models.TextField(blank=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Unique constraint to avoid duplicate products per order
        unique_together = ['order', 'product']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def save(self, *args, **kwargs):
        # Ensure quantity and price are never None
        if self.quantity is None:
            self.quantity = 1
        if self.price is None:
            # Try to get price from product if available
            if self.product and hasattr(self.product, 'price'):
                self.price = self.product.price
            else:
                self.price = 0
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        if self.quantity is None or self.price is None:
            return 0
        return self.quantity * self.price

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name='Order')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Amount')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, verbose_name='Payment Method')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='Transaction ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment for Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update order payment status
        if self.status == 'completed':
            if self.order.remaining_amount <= 0:
                self.order.payment_status = 'paid'
            else:
                self.order.payment_status = 'partial'
            self.order.save(update_fields=['payment_status'])
