import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert

@tool
def send_stock_alert(product_id: str, product_name: str, stock_level: int):
    """
    Envía una alerta de stock bajo invocando la herramienta 'message' de OpenClaw.
    """
    
    # 1. Registro local para visibilidad
    print(f"ALERTA: Stock crítico para {product_name} (ID: {product_id}). Stock actual: {stock_level}")
    
    # 2. Persistencia en Supabase
    db_msg = "OK"
    try:
        LowStockAlert.objects.create(
            product_id=product_id,
            product_name=product_name,
            stock_level=stock_level,
            status="notified"
        )
    except Exception as e:
        db_msg = f"Error DB: {str(e)}"

    # 3. Integración con OpenClaw (Formato Oficial Documentado)
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')

    whatsapp_msg = "Skip"
    
    if gateway_url and gateway_token and recipient_id:
        # Estructura exacta según la guía de integración Django-OpenClaw
        payload = {
            "tool": "message",
            "action": "send",
            "args": {
                "target": recipient_id,
                "message": f"⚠️ *ALERTA DE STOCK BAJO*\n\nEl producto *{product_name}* (SKU: {product_id}) tiene solo *{stock_level}* unidades disponibles.",
                "channel": "whatsapp"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {gateway_token}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"[OPENCLAW DEBUG] Invocando herramienta 'message' en: {gateway_url}")
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                whatsapp_msg = "WhatsApp Enviado"
            else:
                whatsapp_msg = f"Error {response.status_code}"
                print(f"[OPENCLAW DEBUG] Respuesta: {response.text}")
        except Exception as e:
            whatsapp_msg = f"Error Conexión: {str(e)}"

    return f"DB: {db_msg} | WhatsApp: {whatsapp_msg}"
