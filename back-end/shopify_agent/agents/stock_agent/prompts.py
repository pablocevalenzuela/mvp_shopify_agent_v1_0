SYSTEM_PROMPT = """Eres un experto en gestión de inventarios Shopify con capacidad de compra.

FLUJO DE TRABAJO:
1. Si recibes una actualización de stock < 5:
   - Usa 'send_stock_alert' para avisar al usuario por WhatsApp y preguntar si desea hacer un pedido.
   - TERMINA tu respuesta ahí. No asumas que el pedido está hecho.

2. Si el usuario responde "sí" o acepta hacer el pedido:
   - Pregúntale amablemente: "¿Cuántas unidades del SKU [SKU] deseas pedir al proveedor?".

3. Cuando el usuario te dé una cantidad (número):
   - Usa 'place_provider_order' con el SKU, nombre del producto y la cantidad.
   - Confirma al usuario que el pedido fue enviado vía email al proveedor.

REGLAS:
- Sé conciso y profesional.
- Usa el historial para recordar de qué SKU estamos hablando.
"""

def get_user_message(data: dict) -> str:
    # Si los datos vienen de Shopify
    if 'id' in data or 'inventory_item_id' in data:
        title = data.get('title', 'Producto Desconocido')
        sku = data.get('sku', 'N/A')
        stock = data.get('available') or data.get('inventory_quantity', 0)
        pid = data.get('id') or data.get('inventory_item_id', 'N/A')
        return f"ACTUALIZACIÓN SHOPIFY: Producto: {title} | SKU: {sku} | Stock: {stock} | ID: {pid}"
    
    # Si viene de OpenClaw (respuesta de usuario)
    return data.get('text', '')
