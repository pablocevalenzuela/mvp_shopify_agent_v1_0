# Optimización de tokens
SYSTEM_PROMPT = """Eres un asistente de gestión de inventario para Shopify.
Recibirás información de stock de un artículo.
REGLA DE ORO:
1. SÓLO si el stock es MENOR A 5, usa la herramienta 'send_stock_alert'.
2. Si el stock es 5 o mayor, responde: "Stock suficiente ({stock})".
3. Sé conciso.
"""

def get_user_message(data: dict) -> str:
    """Extrae datos ya sea de Product Update o Inventory Level Update."""
    title = data.get('title', 'Producto Desconocido')
    sku = data.get('sku', 'Sin SKU')
    # Detectamos stock de ambos tipos de webhooks
    stock = data.get('inventory_quantity')
    if stock is None:
        stock = data.get('available', 0)
        
    pid = data.get('id') or data.get('inventory_item_id', 'Test-ID')
    
    return f"Producto: {title}, SKU: {sku}, Stock: {stock}, ID: {pid}"
