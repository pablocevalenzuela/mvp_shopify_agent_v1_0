from django.contrib import admin
from .models import Provider, LowStockAlert, ProviderOrder

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'contact_person', 'created_at')
    search_fields = ('name', 'email', 'contact_person')

@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'sku', 'stock_level', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('product_name', 'sku')

@admin.register(ProviderOrder)
class ProviderOrderAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product_name', 'quantity', 'provider_email', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('sku', 'provider_email')
