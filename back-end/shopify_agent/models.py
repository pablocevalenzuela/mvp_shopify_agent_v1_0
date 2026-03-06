from django.db import models

class LowStockAlert(models.Model):
    product_id = models.CharField(max_length=255)
    sku = models.CharField(max_length=255, null=True, blank=True) # Nuevo campo
    product_name = models.CharField(max_length=255)
    stock_level = models.IntegerField()
    status = models.CharField(max_length=50, default='notified')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'low_stock_alerts'
        verbose_name = 'Alerta de Stock Bajo'
        verbose_name_plural = 'Alertas de Stock Bajo'

    def __str__(self):
        return f"{self.product_name} - SKU: {self.sku} - Stock: {self.stock_level}"
