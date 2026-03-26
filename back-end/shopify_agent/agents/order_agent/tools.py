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
    Registra el pedido y ordena a OpenClaw (vía Skill Bundled Himalaya) el envío del correo.
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
    
    # 2. Instrucción a la Skill Bundled Himalaya de OpenClaw
    if gateway_url and gateway_token:
        email_body = (
            f"Pedido de reposición:\n\n"
            f"Producto: {product_name}\n"
            f"SKU: {sku}\n"
            f"Cantidad: {quantity} unidades\n\n"
            f"Saludos, Sistema Automatizado"
        )

        payload = {
            "tool": "himalaya", # Invocación directa de skill bundled
            "action": "send",
            "args": {
                "recipient": provider_email,
                "subject": f"Pedido de Reposición - {product_name} (SKU: {sku})",
                "message": email_body, # Campo estándar para skills bundled
                "gatewayToken": gateway_token
            }
        }
        headers = {
            "Authorization": f"Bearer {gateway_token}",
            "Content-Type": "application/json",
            "X-OpenClaw-Version": "2026.3.13"
        }
        try:
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            print(f"--- [DEBUG] Status: {response.status_code} | Resp: {response.text} ---")
            
            if response.status_code == 200:
                LowStockAlert.objects.filter(sku=sku, status='notified').update(status='processed')
                return f"Pedido enviado exitosamente al proveedor vía Skill Himalaya."
            
            # Intento de fallback con campo 'to' si 'recipient' falla
            if "error" in response.text.lower():
                payload["args"]["to"] = provider_email
                response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
                if response.status_code == 200:
                    return "Pedido enviado exitosamente (usando fallback 'to')."

            return f"Error en OpenClaw al ejecutar Skill Himalaya: {response.text}"
        except Exception as e:
            return f"Error de conexión: {str(e)}"
    return "Configuración de Gateway incompleta."
