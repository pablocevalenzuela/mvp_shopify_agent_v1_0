# Optimización de tokens y precisión de herramientas
SYSTEM_PROMPT = """Eres un asistente de gestión de inventario para Shopify.
Recibirás información de stock de un artículo.

INSTRUCCIONES DE HERRAMIENTAS:
1. SÓLO si el stock es MENOR A 5, usa la herramienta 'send_stock_alert'.
2. Usa UN SOLO ID de producto. Si no lo tienes claro, usa el nombre en minúsculas con guiones.
3. NO llames a la herramienta más de una vez por producto.

RESPUESTAS:
- Si el stock es 5 o mayor, responde: "Stock suficiente ({stock})".
- Si el stock es bajo, informa al usuario si la alerta se guardó exitosamente o si hubo un error técnico.
- Sé extremadamente conciso.
"""

def get_user_message(data: dict) -> str:
    """Extrae datos ya sea de Product Update o Inventory Level Update."""
    title = data.get('title', 'Producto Desconocido')
    sku = data.get('sku', 'Sin SKU')
    stock = data.get('inventory_quantity')
    if stock is None:
        stock = data.get('available', 0)
        
    pid = data.get('id') or data.get('inventory_item_id', 'Test-ID')
    
    return f"Producto: {title}, SKU: {sku}, Stock: {stock}, ID: {pid}"
