from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class StaffUser(AbstractUser):
    """Custom user model for staff members"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('cashier', 'Cashier'),
        ('waiter', 'Waiter'),
        ('kitchen', 'Kitchen'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Role')
    phone_number = models.CharField(max_length=15, verbose_name='Phone Number')
    national_code = models.CharField(max_length=10, unique=True, verbose_name='National Code')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    failed_login_attempts = models.PositiveIntegerField(default=0, verbose_name='Failed Login Attempts')
    last_failed_login = models.DateTimeField(null=True, blank=True, verbose_name='Last Failed Login')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    groups = models.ManyToManyField(
        Group,
        related_name='staffuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='staffuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    class Meta:
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'
        ordering = ['role', 'username']

    def __str__(self):
        return f"{self.get_full_name()} - {self.get_role_display()}"

    def increment_failed_login(self):
        """Increment failed login attempts and update timestamp"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'last_failed_login'])
        # Log failed login attempt
        StaffLog.objects.create(
            staff=self,
            action='login_failed',
            details=f'Failed login attempt #{self.failed_login_attempts}'
        )

    def reset_failed_login(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.save(update_fields=['failed_login_attempts', 'last_failed_login'])
        # Log reset
        StaffLog.objects.create(
            staff=self,
            action='login_reset',
            details='Failed login attempts reset'
        )

    @property
    def is_locked(self):
        """Check if account is locked due to too many failed attempts"""
        if self.failed_login_attempts >= 5:
            # Check if 30 minutes have passed since last failed attempt
            if self.last_failed_login and (timezone.now() - self.last_failed_login).total_seconds() < 1800:
                return True
            # Reset if 30 minutes have passed
            self.reset_failed_login()
        return False

class StaffLog(models.Model):
    """Model for logging staff actions"""
    ACTION_CHOICES = [
        ('login', 'Login to System'),
        ('login_failed', 'Failed Login'),
        ('login_reset', 'Reset Failed Attempts'),
        ('logout', 'Logout from System'),
        ('order_create', 'Create Order'),
        ('order_update', 'Update Order'),
        ('order_cancel', 'Cancel Order'),
        ('payment_create', 'Record Payment'),
        ('payment_refund', 'Refund Payment'),
        ('customer_create', 'Create New Customer'),
        ('customer_update', 'Update Customer Information'),
        ('report_generate', 'Generate Report'),
        ('other', 'Other'),
    ]

    staff = models.ForeignKey(StaffUser, on_delete=models.CASCADE, related_name='logs', verbose_name='Staff Member')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Action')
    details = models.TextField(verbose_name='Details')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Address')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Staff Log'
        verbose_name_plural = 'Staff Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.staff} - {self.get_action_display()} - {self.created_at}"

class Report(models.Model):
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
    ]

    type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='Report Type')
    start_date = models.DateField(verbose_name='Start Date')
    end_date = models.DateField(verbose_name='End Date')
    total_orders = models.PositiveIntegerField(default=0, verbose_name='Total Orders')
    total_revenue = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Total Revenue')
    total_discounts = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Total Discounts')
    created_by = models.ForeignKey(StaffUser, on_delete=models.SET_NULL, null=True, verbose_name='Created By')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.start_date} to {self.end_date}"

    @property
    def net_revenue(self):
        return self.total_revenue - self.total_discounts
