import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder

@tool
def send_stock_alert(product_id: str, sku: str, product_name: str, stock_level: int, thread_id: str = None):
    """
    Envía alerta de bajo stock y pregunta si se desea hacer un pedido al proveedor.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')

    msg_text = (
        f"⚠️ *ALERTA DE STOCK BAJO*\n\n"
        f"El producto *{product_name}* (SKU: {sku}) tiene solo *{stock_level}* unidades.\n\n"
        f"¿Deseas realizar un pedido de reposición? Responde 'SÍ' para comenzar."
    )

    if gateway_url and gateway_token and recipient_id:
        # Limpieza simple del ID si viene con sufijos de OpenClaw
        clean_recipient = recipient_id.split('#')[0].strip()
        payload = {
            "tool": "message",
            "action": "send",
            "args": {"target": clean_recipient, "message": msg_text, "channel": "whatsapp"}
        }
        headers = {"Authorization": f"Bearer {gateway_token}", "Content-Type": "application/json"}
        try:
            requests.post(gateway_url, json=payload, headers=headers, timeout=15)
        except Exception as e:
            print(f"Error enviando alerta a OpenClaw: {e}")

    # Registro en Supabase con thread_id para correlación futura
    LowStockAlert.objects.create(
        product_id=product_id, 
        sku=sku, 
        product_name=product_name, 
        stock_level=stock_level,
        thread_id=thread_id
    )
    
    return f"Alerta enviada para {product_name}. El usuario ha sido notificado en WhatsApp."

@tool
def place_provider_order(sku: str, product_name: str, quantity: int):
    """
    Ordena a OpenClaw enviar un email al proveedor y registra el pedido en el backend.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    provider_email = "proveedor@ejemplo.com" # Esto podría venir de un modelo Provider

    # 1. Registro en Backend (Supabase)
    ProviderOrder.objects.create(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        provider_email=provider_email
    )

    # 2. Ordenar envío de email a OpenClaw
    if gateway_url and gateway_token:
        # Invocamos la herramienta de email de OpenClaw
        email_payload = {
            "tool": "email", # O el nombre que tenga en tu OpenClaw
            "action": "send",
            "args": {
                "to": provider_email,
                "subject": f"Pedido de Reposición - SKU: {sku}",
                "body": f"Estimado proveedor,\n\nSolicitamos un pedido de {quantity} unidades del producto {product_name} (SKU: {sku}).\n\nSaludos."
            }
        }
        headers = {"Authorization": f"Bearer {gateway_token}", "Content-Type": "application/json"}
        requests.post(gateway_url, json=email_payload, headers=headers, timeout=15)

    return f"Pedido de {quantity} unidades de {sku} enviado al proveedor vía OpenClaw."
