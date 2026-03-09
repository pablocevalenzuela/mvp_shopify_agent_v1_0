import os
import requests
import json
from typing import List, Dict, Any
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder, Provider

@tool
def send_stock_alert(product_id: str, sku: str, product_name: str, stock_level: int, thread_id: str = None):
    """
    Envía una alerta de stock bajo al usuario por WhatsApp mediante OpenClaw.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    recipient_id = os.getenv('WHATSAPP_RECIPIENT_ID')

    msg_text = (
        f"⚠️ *ALERTA DE STOCK BAJO*\n\n"
        f"El producto *{product_name}* (SKU: {sku}) tiene solo *{stock_level}* unidades.\n\n"
        f"¿Deseas realizar un pedido de reposición? Responde 'SÍ' para comenzar o 'NO' para ignorar."
    )

    if gateway_url and gateway_token and recipient_id:
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

    LowStockAlert.objects.create(
        product_id=product_id, 
        sku=sku, 
        product_name=product_name, 
        stock_level=stock_level,
        thread_id=thread_id
    )
    
    return f"Alerta enviada para {product_name}. Esperando confirmación del usuario."

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
    return f"Proveedor {name} ({email}) ha sido {status} con éxito en el sistema."

@tool
def place_provider_order(provider_email: str, items_list: str, provider_name: str = None, contact_person: str = None):
    """
    Envía un email formal al proveedor con el pedido de reposición usando OpenClaw.
    'items_list' debe ser un string con el formato: 'SKU1: Cantidad1, SKU2: Cantidad2'.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')

    if not items_list:
        return "Error: No se proporcionaron SKUs para el pedido."

    # Procesar la lista de items para el cuerpo del correo y registro
    items = items_list.split(',')
    formatted_items_text = ""
    for item in items:
        try:
            if ':' not in item: continue
            sku_part, qty_part = item.split(':')
            sku = sku_part.strip()
            qty = int(qty_part.strip())
            formatted_items_text += f"- SKU: {sku} | Cantidad: {qty}\n"
            
            # Registro en la DB para auditoría
            ProviderOrder.objects.create(
                sku=sku,
                product_name="Pedido Agente Stock",
                quantity=qty,
                provider_email=provider_email
            )
        except Exception as e:
            print(f"Error procesando item {item}: {e}")
            continue

    contact_ref = contact_person if contact_person else "Equipo de Ventas"
    body = (
        f"Estimado/a {contact_ref},\n\n"
        f"Espero que este mensaje le encuentre bien. Por medio de la presente, "
        f"solicitamos el siguiente pedido de reposición para nuestra tienda:\n\n"
        f"{formatted_items_text}\n"
        f"Por favor, confírmenos la recepción de este pedido y el tiempo estimado de entrega.\n\n"
        f"Quedamos a la espera de su respuesta.\n"
        f"Saludos cordiales."
    )

    if gateway_url and gateway_token:
        email_payload = {
            "tool": "email",
            "action": "send",
            "args": {
                "to": provider_email,
                "subject": f"Pedido de Reposición - {provider_name if provider_name else 'Tienda'}",
                "body": body
            }
        }
        headers = {"Authorization": f"Bearer {gateway_token}", "Content-Type": "application/json"}
        try:
            response = requests.post(gateway_url, json=email_payload, headers=headers, timeout=15)
            if response.status_code == 200:
                return f"Pedido enviado con éxito a {provider_email} vía OpenClaw."
            else:
                return f"Error al enviar email vía OpenClaw: {response.text}"
        except Exception as e:
            return f"Error de conexión con OpenClaw: {str(e)}"

    return "Error: Configuración de OpenClaw incompleta."
