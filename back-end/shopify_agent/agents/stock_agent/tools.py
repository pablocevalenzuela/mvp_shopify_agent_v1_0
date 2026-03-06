import os
import logging
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert

@tool
def send_stock_alert(product_id: str, product_name: str, stock_level: int):
    """Envía una alerta de stock bajo y persiste en Supabase vía Django ORM."""
    
    # 1. Alerta por consola
    msg = f"ALERTA: Stock crítico para {product_name} (ID: {product_id}). Stock actual: {stock_level}"
    print(msg)
    
    # 2. Persistir en la base de datos usando el ORM de Django
    try:
        # Creamos el registro en la tabla que Django gestiona en Supabase
        alert = LowStockAlert.objects.create(
            product_id=product_id,
            product_name=product_name,
            stock_level=stock_level,
            status="notified"
        )
        return f"Alerta guardada exitosamente en Supabase (ID de registro ORM: {alert.id})"
    except Exception as e:
        error_msg = f"Error al guardar en Supabase vía ORM: {str(e)}"
        print(error_msg)
        return error_msg
