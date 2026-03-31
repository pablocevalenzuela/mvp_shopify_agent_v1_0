import os
import requests
import json
from langchain_core.tools import tool
from shopify_agent.models import LowStockAlert, ProviderOrder, Provider


@tool
def get_pending_stock_alert(thread_id: str):
    """
    Recupera el contexto de la alerta pendiente desde la base de datos local.
    Soporta búsqueda robusta para coincidir con el thread_id de Supabase.
    """
    try:
        # 1. Limpieza agresiva del ID entrante (WhatsApp -> Solo dígitos)
        clean_id = "".join(filter(str.isdigit, str(thread_id)))
        
        # 2. Búsqueda por coincidencia parcial (los últimos 9 dígitos son el ancla de identidad)
        # Esto funciona tanto si en la BD está con prefijo o sin él.
        suffix = clean_id[-9:] if len(clean_id) >= 9 else clean_id
        
        print(f"--- [DEBUG AGENT] Buscando alerta en Supabase para sufijo: {suffix} ---")
        
        alert = LowStockAlert.objects.filter(
            thread_id__contains=suffix, 
            status='notified'
        ).order_by('-created_at').first()

        if alert:
            print(f"--- [DEBUG AGENT] Alerta encontrada: {alert.product_name} (ID: {alert.id}) ---")
            return {
                "sku": alert.sku,
                "product_name": alert.product_name,
                "current_stock": alert.stock_level,
                "vendor": alert.vendor,
                "alert_id": alert.id
            }
        
        print(f"--- [DEBUG AGENT] No se encontró ninguna alerta 'notified' para {suffix} ---")
        return "No se encontraron alertas de bajo stock activas para este usuario. Pídele al usuario que espere a una nueva alerta."
    except Exception as e:
        return f"Error en el dominio al buscar la alerta: {str(e)}"


@tool
def find_best_provider_for_sku(sku: str):
    """
    Busca el proveedor adecuado para un SKU específico en la base de datos privada.
    """
    # Intentamos buscar el proveedor asociado al SKU o devolvemos el primero por defecto
    provider = Provider.objects.first()
    if provider:
        return {
            "name": provider.name,
            "email": provider.email,
            "contact": provider.contact_person
        }
    return {"error": "No hay proveedores registrados en el sistema."}


@tool
def place_provider_order(sku: str, product_name: str, quantity: int, provider_email: str, thread_id: str = None):
    """
    Registra el pedido y retorna los datos para que el Hook local de la VM envíe el correo vía Himalaya.
    Marca automáticamente la alerta como 'processed' para evitar duplicados.
    """
    print(f"--- [HIMALAYA PAYLOAD] Generando datos para {provider_email} (Cantidad: {quantity}) ---")
    
    # 1. Registro de auditoría local del pedido
    order = ProviderOrder.objects.create(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        provider_email=provider_email
    )
    
    # 2. SEGURIDAD DE ESTADO: Marcar la alerta como procesada
    if thread_id:
        clean_id = "".join(filter(str.isdigit, str(thread_id)))
        suffix = clean_id[-9:] if len(clean_id) >= 9 else clean_id
        
        # Buscamos la alerta 'notified' más reciente para este producto y usuario
        alert = LowStockAlert.objects.filter(
            thread_id__contains=suffix,
            sku=sku,
            status='notified'
        ).order_by('-created_at').first()
        
        if alert:
            alert.status = 'processed'
            alert.save()
            print(f"--- [STATE SECURITY] Alerta {alert.id} marcada como PROCESADA ---")
        else:
            print(f"--- [STATE WARNING] No se encontró alerta 'notified' para cerrar (User: {suffix}, SKU: {sku}) ---")
    
    # 3. Preparación del cuerpo del mensaje
    email_body = (
        f"Pedido de reposición:\n\n"
        f"Producto: {product_name}\n"
        f"SKU: {sku}\n"
        f"Cantidad: {quantity} unidades\n\n"
        f"Saludos, Sistema Automatizado"
    )

    # Retornamos el objeto que el script 'whatsapp_filter.py' en la VM espera detectar
    return {
        "action": "send_himalaya_email",
        "order_id": order.id,
        "recipient": provider_email,
        "subject": f"Pedido de Reposición - {product_name} (SKU: {sku})",
        "body": email_body,
        "success_msg": f"✅ Pedido procesado: {quantity} unidades de {product_name} enviadas a {provider_email}."
    }
