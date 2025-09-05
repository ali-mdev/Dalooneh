from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from .models import Customer, CustomerRating, Discount

class CustomerRatingInline(admin.TabularInline):
    model = CustomerRating
    extra = 0
    readonly_fields = ['created_at']

class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_full_name', 'phone_number', 'membership_level', 'total_points', 'orders_count', 'total_spent', 'is_active', 'created_at']
    list_filter = ['membership_level', 'is_active', 'created_at']
    search_fields = ['phone_number', 'national_code', 'user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['total_points', 'total_spent', 'total_orders', 'orders_link', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [CustomerRatingInline, DiscountInline]
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone_number', 'national_code')
        }),
        ('Personal Information', {
            'fields': ('address', 'birth_date')
        }),
        ('Membership Status', {
            'fields': ('membership_level', 'total_points', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_orders', 'total_spent', 'orders_link')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user.first_name or obj.user.last_name else obj.user.username
    user_full_name.short_description = 'Customer Name'
    
    def orders_count(self, obj):
        count = obj.orders.count()
        if count:
            url = reverse('admin:orders_order_changelist') + f'?customer__id__exact={obj.id}'
            return format_html('<a href="{}">{} Orders</a>', url, count)
        return '0 Orders'
    orders_count.short_description = 'Orders Count'
    
    def total_spent(self, obj):
        total = obj.orders.aggregate(total=Sum('final_amount'))['total'] or 0
        return f"${total:,.2f}"
    total_spent.short_description = 'Total Spent'
    
    def orders_link(self, obj):
        url = reverse('admin:orders_order_changelist') + f'?customer__id__exact={obj.id}'
        return format_html('<a class="button" href="{}">View Orders for This Customer</a>', url)
    orders_link.short_description = 'Orders'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            orders_count=Count('orders', distinct=True)
        )
        return queryset

@admin.register(CustomerRating)
class CustomerRatingAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'order', 'rating', 'comment', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['customer__phone_number', 'order__order_number', 'comment']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'code', 'percentage', 'is_active', 'valid_from', 'valid_to']
    list_filter = ['is_active', 'valid_from', 'valid_to', 'percentage']
    search_fields = ['customer__phone_number', 'code']
    readonly_fields = ['created_at', 'updated_at']
