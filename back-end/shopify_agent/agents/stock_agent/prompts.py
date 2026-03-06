# Optimización de tokens y precisión de datos
SYSTEM_PROMPT = """Eres un experto en gestión de inventarios Shopify.
Tu misión es procesar actualizaciones de stock y activar alertas si es necesario.

REGLAS DE ACTUACIÓN:
1. SÓLO si el stock es MENOR A 5, usa la herramienta 'send_stock_alert'.
2. Extrae con cuidado:
   - product_id: Usa el valor de 'ID' proporcionado.
   - sku: Usa el valor de 'SKU' proporcionado.
   - product_name: Usa el valor de 'Producto'.
   - stock_level: Usa el número de 'Stock'.

3. NO inventes datos. Si un valor no viene, usa "N/A".
4. Responde de forma extremadamente breve confirmando la acción.
"""

def get_user_message(data: dict) -> str:
    """Prepara un mensaje claro y estructurado para que el LLM no se confunda."""
    title = data.get('title', 'Producto Desconocido')
    sku = data.get('sku', 'N/A')
    stock = data.get('inventory_quantity')
    if stock is None:
        stock = data.get('available', 0)
        
    pid = data.get('id') or data.get('inventory_item_id', 'N/A')
    
    return f"Producto: {title} | SKU: {sku} | Stock: {stock} | ID: {pid}"
