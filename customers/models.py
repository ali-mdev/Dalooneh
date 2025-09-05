from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum

class Customer(models.Model):
    MEMBERSHIP_CHOICES = [
        ('regular', 'Regular'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer', verbose_name='User')
    phone_number = models.CharField(max_length=15, unique=True, verbose_name='Phone Number')
    national_code = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name='National ID')
    address = models.TextField(blank=True, verbose_name='Address')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Birth Date')
    total_points = models.PositiveIntegerField(default=0, verbose_name='Total Points')
    membership_level = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_CHOICES,
        default='regular',
        verbose_name='Membership Level'
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone_number}"

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_spent(self):
        return self.orders.aggregate(total=Sum('final_amount'))['total'] or 0

    def update_membership_level(self):
        """Update membership level based on total points"""
        if self.total_points >= 10000:
            self.membership_level = 'platinum'
        elif self.total_points >= 5000:
            self.membership_level = 'gold'
        elif self.total_points >= 1000:
            self.membership_level = 'silver'
        else:
            self.membership_level = 'regular'
        self.save(update_fields=['membership_level'])

    def add_points(self, points):
        """Add points to customer's total"""
        self.total_points += points
        self.save(update_fields=['total_points'])
        self.update_membership_level()

class CustomerRating(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ratings', verbose_name='Customer')
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='rating', verbose_name='Order')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Rating'
    )
    comment = models.TextField(blank=True, verbose_name='Comment')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Rating'
        verbose_name_plural = 'Customer Ratings'
        ordering = ['-created_at']

    def __str__(self):
        return f"Rating {self.rating} from {self.customer}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Add points based on rating
            points = self.rating * 10  # 10 points per star
            self.customer.add_points(points)

class Discount(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='discounts', verbose_name='Customer')
    code = models.CharField(max_length=20, unique=True, verbose_name='Discount Code')
    percentage = models.PositiveIntegerField(verbose_name='Discount Percentage')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    valid_from = models.DateTimeField(verbose_name='Valid From')
    valid_to = models.DateTimeField(verbose_name='Valid To')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Discount'
        verbose_name_plural = 'Discounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.percentage}%"

    def is_valid(self):
        """Check if discount is valid"""
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to
        )
