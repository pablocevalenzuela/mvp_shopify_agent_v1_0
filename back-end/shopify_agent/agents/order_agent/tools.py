import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder, Provider


@tool
def get_pending_stock_alert(thread_id: str):
    """
    Recupera el contexto de la alerta pendiente desde la base de datos local.
    """
    try:
        alert = LowStockAlert.objects.filter(
            thread_id=thread_id, status='notified').order_by('-created_at').first()
        if alert:
            return {
                "sku": alert.sku,
                "product_name": alert.product_name,
                "current_stock": alert.stock_level,
                "vendor": alert.vendor,
                "alert_id": alert.id
            }
        return "No se encontraron alertas de bajo stock activas para este usuario."
    except Exception as e:
        return f"Error en el dominio al buscar la alerta: {str(e)}"


@tool
def find_best_provider_for_sku(sku: str):
    """
    Busca el proveedor adecuado para un SKU específico en la base de datos privada.
    """
    provider = Provider.objects.first()
    if provider:
        return {
            "name": provider.name,
            "email": provider.email,
            "contact": provider.contact_person
        }
    return {"error": "No hay proveedores registrados para este producto."}


@tool
def place_provider_order(sku: str, product_name: str, quantity: int, provider_email: str):
    """
    Registra el pedido y ordena a OpenClaw (vía Skill Himalaya) el envío del correo.
    """
    print(f"--- [HIMALAYA] Intentando enviar pedido a {provider_email} ---")
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    
    # 1. Registro de auditoría local
    ProviderOrder.objects.create(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        provider_email=provider_email
    )
    
    # 2. Instrucción a la Skill Himalaya de OpenClaw
    if gateway_url and gateway_token:
        # Formateamos el cuerpo del correo de forma profesional
        email_body = (
            f"Estimado proveedor,\n\n"
            f"Solicitamos formalmente el pedido de reposición para el siguiente producto:\n\n"
            f"- Producto: {product_name}\n"
            f"- SKU: {sku}\n"
            f"- Cantidad: {quantity} unidades\n\n"
            f"Por favor, confírmenos la recepción de este pedido y el tiempo estimado de entrega.\n\n"
            f"Saludos,\nAgente de Compras Automatizado"
        )

        payload = {
            "tool": "email.send", # Nombre técnico estándar en OpenClaw v2026.3.13
            "action": "send",
            "args": {
                "to": provider_email,
                "subject": f"Pedido de Reposición - {product_name} (SKU: {sku})",
                "body": email_body,
                "gatewayToken": gateway_token
            }
        }
        headers = {
            "Authorization": f"Bearer {gateway_token}",
            "Content-Type": "application/json",
            "X-OpenClaw-Version": "2026.3.13"
        }
        try:
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=12)
            print(f"--- [DEBUG] Status: {response.status_code} | Resp: {response.text} ---")
            
            if response.status_code == 200:
                # Marcamos la alerta como procesada
                LowStockAlert.objects.filter(sku=sku, status='notified').update(status='processed')
                return f"Pedido de {quantity} unidades enviado exitosamente al proveedor {provider_email} vía Himalaya."
            
            # Fallback si el nombre técnico falla
            if "Tool not available" in response.text:
                payload["tool"] = "himalaya.send"
                response = requests.post(gateway_url, json=payload, headers=headers, timeout=12)
                if response.status_code == 200:
                    return f"Pedido enviado exitosamente (fallback: himalaya.send)."

            return f"OpenClaw recibió la orden pero reportó un error: {response.text}"
        except Exception as e:
            return f"Error de conexión al intentar enviar con Himalaya: {str(e)}"
    return "Configuración de Gateway incompleta."
