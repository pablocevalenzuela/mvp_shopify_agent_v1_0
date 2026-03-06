import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert

@tool
def send_stock_alert(product_id: str, product_name: str, stock_level: int):
    """
    Envía una alerta de stock bajo vía OpenClaw Gateway.
    """
    
    # 1. Registro local
    print(f"ALERTA: Stock crítico para {product_name} (ID: {product_id}). Stock actual: {stock_level}")
    
    # 2. Persistencia en Supabase
    try:
        LowStockAlert.objects.create(
            product_id=product_id,
            product_name=product_name,
            stock_level=stock_level,
            status="notified"
        )
        db_status = "Supabase OK"
    except Exception as e:
        db_status = f"DB Error: {str(e)}"

    # 3. Notificación WhatsApp vía OpenClaw Gateway
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')

    whatsapp_status = "WhatsApp Skip"
    
    if gateway_url and gateway_token and recipient_id:
        # Formato para el endpoint /v1/messages/send del Gateway
        payload = {
            "channel": "whatsapp",
            "to": recipient_id,
            "message": f"⚠️ *ALERTA DE STOCK BAJO*\n\nEl producto *{product_name}* (SKU: {product_id}) tiene solo *{stock_level}* unidades disponibles.",
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gateway_token}"
        }
        
        try:
            # Enviamos la petición al puerto 18789 de la VM en GCP
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            
            if response.status_code in [200, 201, 202]:
                whatsapp_status = "WhatsApp OK"
            else:
                whatsapp_status = f"OpenClaw Error: {response.status_code}"
                print(f"[OPENCLAW DEBUG] URL intentada: {gateway_url}")
                print(f"[OPENCLAW DEBUG] Respuesta: {response.text}")
        except Exception as e:
            whatsapp_status = f"Conn Error: {str(e)}"

    return f"Resultado: {db_status} | {whatsapp_status}."
