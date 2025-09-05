from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .models import Table, TableSession

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'seats', 'is_active', 'is_occupied', 'qr_code_display', 'created_at')
    list_filter = ('is_active', 'seats')
    search_fields = ('number',)
    ordering = ('number',)
    actions = ['generate_qr_codes', 'activate_tables', 'deactivate_tables']
    
    def is_occupied(self, obj):
        return obj.is_occupied
    is_occupied.boolean = True
    is_occupied.short_description = 'Occupied'
    
    def qr_code_display(self, obj):
        if obj.qr_code:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="50" height="50" /></a>',
                obj.qr_code.url,
                obj.qr_code.url
            )
        return '-'
    qr_code_display.short_description = 'QR Code'
    
    def generate_qr_codes(self, request, queryset):
        for table in queryset:
            table.generate_qr_code()
        self.message_user(request, f'QR codes generated for {queryset.count()} tables.')
    generate_qr_codes.short_description = 'Generate QR codes for selected tables'
    
    def activate_tables(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} tables activated.')
    activate_tables.short_description = 'Activate selected tables'
    
    def deactivate_tables(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} tables deactivated.')
    deactivate_tables.short_description = 'Deactivate selected tables'

@admin.register(TableSession)
class TableSessionAdmin(admin.ModelAdmin):
    list_display = ('table', 'token', 'is_active', 'is_expired', 'created_at', 'expires_at', 'last_used')
    list_filter = ('is_active', 'table')
    search_fields = ('table__number', 'token')
    ordering = ('-created_at',)
    readonly_fields = ('token', 'created_at', 'expires_at', 'last_used')
    actions = ['deactivate_sessions']
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    def deactivate_sessions(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} sessions deactivated.')
    deactivate_sessions.short_description = 'Deactivate selected sessions'
