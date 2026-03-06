import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert

@tool
def send_stock_alert(product_id: str, product_name: str, stock_level: int):
    """
    Envía una alerta de stock bajo:
    1. Registra en Consola de Django.
    2. Persiste en Supabase (PostgreSQL).
    3. Envía notificación de WhatsApp vía el plugin Universal IM de OpenClaw en GCP.
    """
    
    # 1. Registro en Consola para debug local
    print(f"ALERTA: Stock crítico para {product_name} (ID: {product_id}). Stock actual: {stock_level}")
    
    # 2. Persistencia en Supabase vía Django ORM
    db_status = "Error en DB"
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

    # 3. Notificación WhatsApp vía OpenClaw Universal IM
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')

    whatsapp_status = "WhatsApp Skip"
    
    if gateway_url and gateway_token and recipient_id:
        # Formato oficial para el plugin Universal IM de OpenClaw
        payload = {
            "channel": "whatsapp",
            "to": recipient_id,
            "content": f"⚠️ *ALERTA DE STOCK BAJO*\n\nEl producto *{product_name}* (SKU: {product_id}) tiene solo *{stock_level}* unidades en stock.\n\nFavor revisar en el Admin de Shopify.",
            "type": "text"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gateway_token}",
            "X-OpenClaw-Source": "Shopify-Agent"
        }
        
        try:
            # Enviamos la petición al Gateway de OpenClaw en la VM de GCP
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=12)
            
            if response.status_code in [200, 201, 202]:
                whatsapp_status = "WhatsApp OK"
            else:
                whatsapp_status = f"OpenClaw Error: {response.status_code}"
                print(f"[OPENCLAW DEBUG] Detalle: {response.text}")
        except Exception as e:
            whatsapp_status = f"Conn Error: {str(e)}"
            print(f"[OPENCLAW DEBUG] Fallo de conexión: {e}")

    return f"Resultado: {db_status} | {whatsapp_status}."
