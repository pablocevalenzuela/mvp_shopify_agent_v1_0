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
    Registra el pedido y retorna los datos para que OpenClaw envíe el correo vía Himalaya.
    """
    print(f"--- [HIMALAYA] Preparando pedido para {provider_email} ---")
    
    # 1. Registro de auditoría local (No se rompe la trazabilidad)
    order = ProviderOrder.objects.create(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        provider_email=provider_email
    )
    
    email_body = (
        f"Pedido de reposición:\n\n"
        f"Producto: {product_name}\n"
        f"SKU: {sku}\n"
        f"Cantidad: {quantity} unidades\n\n"
        f"Saludos, Sistema Automatizado"
    )

    # Retornamos un objeto estructurado que la View y el Hook usarán
    return {
        "action": "send_himalaya_email",
        "order_id": order.id,
        "recipient": provider_email,
        "subject": f"Pedido de Reposición - {product_name} (SKU: {sku})",
        "body": email_body,
        "success_msg": f"✅ Pedido procesado: {quantity} unidades de {product_name} enviadas a {provider_email}."
    }
