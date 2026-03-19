import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder, Provider

@tool
def get_pending_stock_alert(thread_id: str):
    """
    Recupera el contexto de la alerta pendiente desde la base de datos local.
    Este es un dato privado del dominio que OpenClaw no conoce.
    """
    try:
        alert = LowStockAlert.objects.filter(thread_id=thread_id, status='notified').order_by('-created_at').first()
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
    Usa esta herramienta antes de realizar un pedido.
    """
    # En un sistema real, podrías tener una tabla de mapeo Producto-Proveedor.
    # Aquí buscaremos un proveedor que coincida con el nombre o simplemente el principal.
    provider = Provider.objects.first() # Lógica simplificada: aquí reside tu dominio privado
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
    Registra el pedido y ordena a OpenClaw (Gateway) el envío del correo.
    Toda la lógica de quién es el proveedor ya fue resuelta por el agente en el backend.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')

    # 1. Registro de auditoría local (Información privada de negocio)
    ProviderOrder.objects.create(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        provider_email=provider_email
    )

    # 2. Instrucción atómica al Gateway (OpenClaw v2026.3.13)
    if gateway_url and gateway_token:
        payload = {
            "tool": "skill",
            "action": "execute",
            "args": {
                "id": "send_provider_order_email",
                "recipient": provider_email,
                "data": {
                    "sku": sku,
                    "product": product_name,
                    "quantity": quantity
                }
            }
        }
        headers = {
            "Authorization": f"Bearer {gateway_token}", 
            "Content-Type": "application/json",
            "X-OpenClaw-Version": "2026.3.13"
        }
        try:
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                # Marcamos la alerta como procesada en el dominio local
                LowStockAlert.objects.filter(sku=sku, status='notified').update(status='processed')
                return f"Orden enviada a OpenClaw exitosamente para {provider_email}."
            return f"Error al delegar envío a OpenClaw: {response.text}"
        except Exception as e:
            return f"Error de conexión con el Gateway: {str(e)}"

    return "Configuración de Gateway incompleta."
