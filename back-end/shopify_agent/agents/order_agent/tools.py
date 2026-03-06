import os
import requests
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder

@tool
def get_pending_stock_alert(thread_id: str):
    """
    Obtiene la última alerta de bajo stock para una conversación específica (thread_id).
    Permite al agente saber qué producto necesita reposición sin que el usuario lo diga de nuevo.
    """
    try:
        alert = LowStockAlert.objects.filter(thread_id=thread_id).order_by('-created_at').first()
        if alert:
            return {
                "sku": alert.sku,
                "product_name": alert.product_name,
                "current_stock": alert.stock_level,
                "id": alert.id
            }
        return "No se encontraron alertas recientes para este usuario."
    except Exception as e:
        return f"Error al buscar la alerta: {str(e)}"

@tool
def place_provider_order(sku: str, product_name: str, quantity: int):
    """
    Registra el pedido en el backend y envía el email al proveedor vía OpenClaw.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    provider_email = "proveedor@ejemplo.com" # TODO: Configurar dinámico si existe modelo Provider

    # 1. Registro en Backend
    ProviderOrder.objects.create(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        provider_email=provider_email
    )

    # 2. Ordenar envío de email a OpenClaw
    if gateway_url and gateway_token:
        email_payload = {
            "tool": "email",
            "action": "send",
            "args": {
                "to": provider_email,
                "subject": f"Pedido de Reposición - SKU: {sku}",
                "body": f"Estimado proveedor,\n\nSolicitamos un pedido de {quantity} unidades del producto {product_name} (SKU: {sku}).\n\nSaludos."
            }
        }
        headers = {"Authorization": f"Bearer {gateway_token}", "Content-Type": "application/json"}
        try:
            requests.post(gateway_url, json=email_payload, headers=headers, timeout=15)
        except Exception as e:
            print(f"Error enviando email a OpenClaw: {e}")

    return f"Pedido de {quantity} unidades de {product_name} (SKU: {sku}) enviado al proveedor."
