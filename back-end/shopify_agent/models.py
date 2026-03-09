from django.db import models

class LowStockAlert(models.Model):
    product_id = models.CharField(max_length=255)
    sku = models.CharField(max_length=255, null=True, blank=True)
    product_name = models.CharField(max_length=255)
    stock_level = models.IntegerField()
    status = models.CharField(max_length=50, default='notified')
    thread_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'low_stock_alerts'

class Provider(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'providers'

    def __str__(self):
        return f"{self.name} ({self.email})"

class ProviderOrder(models.Model):
    sku = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    provider_email = models.EmailField()
    status = models.CharField(max_length=50, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'provider_orders'

    def __str__(self):
        return f"Pedido {self.sku} - Cantidad: {self.quantity}"
