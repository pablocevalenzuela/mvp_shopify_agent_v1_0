import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert

@tool
def send_stock_alert(product_id: str, sku: str, product_name: str, stock_level: int):
    """
    Envía una alerta de stock bajo.
    Argumentos: product_id (ID de Shopify), sku, product_name, stock_level.
    """
    
    # 1. Registro local
    print(f"ALERTA: Stock crítico para {product_name} (SKU: {sku}). Stock actual: {stock_level}")
    
    # 2. Persistencia en Supabase
    try:
        LowStockAlert.objects.create(
            product_id=product_id,
            sku=sku,
            product_name=product_name,
            stock_level=stock_level,
            status="notified"
        )
        db_msg = "OK"
    except Exception as e:
        db_msg = f"Error DB: {str(e)}"

    # 3. Integración con OpenClaw
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')

    whatsapp_msg = "Skip"
    
    if gateway_url and gateway_token and recipient_id:
        recipient_id = recipient_id.split('#')[0].strip()
        
        payload = {
            "tool": "message",
            "action": "send",
            "args": {
                "target": recipient_id,
                "message": f"⚠️ *ALERTA DE STOCK BAJO*\n\nEl producto *{product_name}* (SKU: {sku}) tiene solo *{stock_level}* unidades disponibles.",
                "channel": "whatsapp"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {gateway_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            whatsapp_msg = "WhatsApp Enviado" if response.status_code == 200 else f"Error {response.status_code}"
        except Exception as e:
            whatsapp_msg = f"Error Conexión: {str(e)}"

    return f"DB: {db_msg} | WhatsApp: {whatsapp_msg}"
