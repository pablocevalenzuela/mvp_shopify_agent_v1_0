# Optimización de tokens: Instrucciones directas, sin relleno ("Few-shot" opcional para claridad)
SYSTEM_PROMPT = """Eres un asistente de gestión de inventario para Shopify.
Recibirás información de stock de un artículo.
REGLA DE ORO:
1. SÓLO si el stock es MENOR A 5, usa la herramienta 'send_stock_alert'.
2. Si el stock es 5 o mayor, NO hagas NADA y responde brevemente: "Stock suficiente ({stock})".
3. NO repitas el historial. Sé conciso para ahorrar costos de tokens.
4. Si usas 'send_stock_alert', incluye el ID del producto, el nombre y el nivel actual de stock.
"""

def get_user_message(product_data: dict) -> str:
    """Extrae solo lo relevante del webhook para no inundar el contexto del LLM."""
    return f"Producto: {product_data.get('title')}, SKU: {product_data.get('sku')}, Stock: {product_data.get('inventory_quantity')}, ID: {product_data.get('id')}"
