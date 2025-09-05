from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, Payment
from django import forms
from django.shortcuts import redirect
from django.urls import path
from django.contrib.admin import SimpleListFilter

class PhoneNumberSearchForm(forms.Form):
    phone_number = forms.CharField(max_length=15, required=True, label='Search by phone number')

class PhoneNumberFilter(SimpleListFilter):
    title = 'Customer phone number'
    parameter_name = 'customer__phone_number'
    
    def lookups(self, request, model_admin):
        """
        Returns unique phone numbers of customers with orders
        """
        phone_numbers = set()
        for order in Order.objects.select_related('customer').all():
            if order.customer and order.customer.phone_number:
                phone_numbers.add(order.customer.phone_number)
        return [(phone, phone) for phone in sorted(phone_numbers)]
    
    def queryset(self, request, queryset):
        """
        Returns all orders for the selected customer phone number
        """
        if self.value():
            return queryset.filter(customer__phone_number=self.value())
        return queryset

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['get_total_price']
    fields = ['product', 'quantity', 'price', 'get_total_price', 'notes']
    
    def get_total_price(self, obj):
        try:
            if obj.quantity is None or obj.price is None:
                return '0'
            total = obj.quantity * obj.price
            return f"{total:,}"
        except (TypeError, AttributeError):
            return '0'
    get_total_price.short_description = 'Total Price'

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['amount', 'payment_method', 'status', 'transaction_id', 'created_at']
    readonly_fields = ['created_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'get_customer_phone', 'table', 'status', 'payment_status', 'total_amount', 'final_amount', 'created_at']
    list_filter = [PhoneNumberFilter, 'status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'customer__phone_number', 'customer__user__first_name', 'customer__user__last_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'get_customer_phone']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline, PaymentInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'get_customer_phone', 'table')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Financial', {
            'fields': ('total_amount', 'discount_amount', 'final_amount')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_customer_phone(self, obj):
        if obj.customer and obj.customer.phone_number:
            # Clickable phone number to filter orders by that phone
            url = f"?customer__phone_number={obj.customer.phone_number}"
            return format_html('<a href="{}">{}</a>', url, obj.customer.phone_number)
        return '-'
    get_customer_phone.short_description = 'Customer phone'
    get_customer_phone.admin_order_field = 'customer__phone_number'
    
    # Add search-by-phone form
    change_list_template = 'admin/orders/order/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('search-by-phone/', self.admin_site.admin_view(self.search_by_phone), name='search_by_phone'),
        ]
        return custom_urls + urls
    
    def search_by_phone(self, request):
        if request.method == 'POST':
            form = PhoneNumberSearchForm(request.POST)
            if form.is_valid():
                phone_number = form.cleaned_data['phone_number']
                return redirect(f'admin:orders_order_changelist?customer__phone_number={phone_number}')
        return redirect('admin:orders_order_changelist')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'get_quantity', 'get_price', 'get_total_price', 'created_at']
    list_filter = ['order__status', 'created_at']
    search_fields = ['order__order_number', 'product__name', 'order__customer__phone_number']
    readonly_fields = ['get_total_price', 'created_at']
    
    def get_quantity(self, obj):
        return obj.quantity or 0
    get_quantity.short_description = 'Quantity'
    get_quantity.admin_order_field = 'quantity'
    
    def get_price(self, obj):
        if obj.price is None:
            return '0'
        return f"{obj.price:,}"
    get_price.short_description = 'Unit Price'
    get_price.admin_order_field = 'price'
    
    def get_total_price(self, obj):
        try:
            total = obj.total_price
            return f"{total:,}"
        except (TypeError, AttributeError):
            return '0'
    get_total_price.short_description = 'Total Price'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['order__order_number', 'transaction_id', 'order__customer__phone_number']
    readonly_fields = ['created_at', 'updated_at']
