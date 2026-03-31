import os
import requests
import json
from typing import List, Dict, Any
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder, Provider


@tool
def send_stock_alert(product_id: str, sku: str, product_name: str, stock_level: int, vendor: str = None, thread_id: str = None):
    """
    Envía una alerta de stock bajo al usuario por WhatsApp mediante OpenClaw.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')
    vendor_info = f" del proveedor *{vendor}*" if vendor else ""
    msg_text = (
        f"⚠️ *ALERTA DE STOCK BAJO*\n\n"
        f"El producto *{product_name}* (SKU: {sku}){vendor_info} tiene solo *{stock_level}* unidades restantes. "
        f"Para hacer un nuevo pedido de reposición responde con un *si* o */hacer_pedido*, añade la cantidad a reponer "
        f"o responde con un *no* para ignorar esta alerta."
    )
    if gateway_url and gateway_token and recipient_id:
        clean_recipient = recipient_id.split('#')[0].strip()
        # Payload optimizado para v2026.3.13 (Formato Plano)
        payload = {
            "tool": "message",
            "action": "send",
            "args": {
                "recipient_id": clean_recipient,
                "message": msg_text,
                "channel": "whatsapp"
            }
        }
        headers = {
            "Authorization": f"Bearer {gateway_token}",
            "Content-Type": "application/json",
            "X-OpenClaw-Version": "2026.3.13"
        }
        try:
            response = requests.post(gateway_url, json=payload,
                                     headers=headers, timeout=20)
            
            # Verificación proactiva del status
            if response.status_code == 200:
                print(f"--- [OPENCLAW TOOL SUCCESS] Alerta enviada correctamente a {clean_recipient} ---")
            else:
                print(f"--- [OPENCLAW TOOL ERROR] Status: {response.status_code} | Response: {response.text} ---")
                return f"Error al enviar alerta vía OpenClaw: {response.text}"
                
        except Exception as e:
            print(f"Error crítico en conexión con OpenClaw: {e}")
            return f"Excepción de red al enviar alerta: {str(e)}"
    LowStockAlert.objects.create(
        product_id=product_id,
        sku=sku,
        product_name=product_name,
        vendor=vendor,
        stock_level=stock_level,
        thread_id=thread_id
    )

    return f"Alerta enviada para {product_name} (Proveedor: {vendor}). Esperando confirmación."


@tool
def check_provider_info(email: str = None, name: str = None):
    """
    Busca información de un proveedor por su email o nombre en la base de datos local.
    Retorna los datos del proveedor si existe, o un mensaje indicando que no se encontró.
    """
    try:
        if email:
            provider = Provider.objects.get(email=email)
        elif name:
            provider = Provider.objects.get(name__icontains=name)
        else:
            return "Error: Debes proporcionar un email o nombre para buscar."

        return {
            "found": True,
            "name": provider.name,
            "email": provider.email,
            "contact_person": provider.contact_person
        }
    except Provider.DoesNotExist:
        return {"found": False, "message": "Proveedor no encontrado en la base de datos."}


@tool
def register_provider(name: str, email: str, contact_person: str):
    """
    Registra o actualiza un proveedor en la base de datos.
    Úsalo cuando el usuario te proporcione los datos de un proveedor nuevo.
    """
    provider, created = Provider.objects.update_or_create(
        email=email,
        defaults={'name': name, 'contact_person': contact_person}
    )
    status = "registrado" if created else "actualizado"
    return f"Proveedor {name} ({email}) ha sido {status} correctamente."
