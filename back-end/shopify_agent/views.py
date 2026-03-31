import hmac
import hashlib
import json
import base64
import os
import requests
import re
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from shopify_agent.agents.stock_agent.runner import run_stock_agent
from shopify_agent.agents.order_agent.runner import run_order_agent
from shopify_agent.models import LowStockAlert, Provider


def verify_shopify_webhook(data, hmac_header):
    secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')
    if not secret:
        return False
    secret = secret.encode('utf-8')
    digest = base64.b64encode(
        hmac.new(secret, data, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(digest, hmac_header)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_webhook_receiver(request):
    """
    Webhook de Inventario de Shopify: Dispara alertas de bajo stock.
    """
    print(f"\n--- [WEBHOOK SHOPIFY] Nueva notificación de inventario ---")
    try:
        request_body = request.body
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')
        if not hmac_header or not verify_shopify_webhook(request_body, hmac_header):
            print("--- [WEBHOOK ERROR] HMAC no válido ---")
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        payload = json.loads(request_body.decode('utf-8'))

        # Enviamos la alerta al número configurado por defecto
        thread_id = os.getenv('WHATSAPP_RECIPIENT_ID', 'shopify_admin')
        result = run_stock_agent(payload, thread_id=thread_id)
        return JsonResponse(result)
    except Exception as e:
        print(f"--- [WEBHOOK ERROR GLOBAL] {e} ---")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def openclaw_response_receiver(request):
    """
    RECEPTOR PRINCIPAL DE OPENCLAW (WHATSAPP).
    """
    print("\n" + "="*50)
    print(f"!!! [CRITICAL DEBUG] PETICIÓN ENTRANTE DESDE OPENCLAW !!!")
    print(f"Timestamp: {os.getloadavg()}") # Solo para ver algo dinámico
    print("="*50)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        # 1. Extracción y Normalización agresiva del ID
        user_msg = (
            payload.get('body') or 
            payload.get('text') or 
            payload.get('message') or 
            payload.get('data', {}).get('content', '')
        )
        user_msg = user_msg.strip() if user_msg else ""
        
        raw_user_id = (
            payload.get('bsuid') or 
            payload.get('sender_id') or 
            payload.get('sender') or 
            payload.get('from') or
            os.getenv('WHATSAPP_RECIPIENT_ID', 'default_user')
        )
        
        # Limpieza total: Solo números. (Ej: +56 9... -> 569...)
        user_id = "".join(filter(str.isdigit, str(raw_user_id)))

        print(f"--- [ROUTER DEBUG] Msg: '{user_msg}' | User: {user_id} ---")

        user_msg_lower = user_msg.lower()
        is_order_command = "/hacer_pedido" in user_msg_lower or "/hacer pedido" in user_msg_lower
        is_confirmation = any(word in user_msg_lower for word in ['si', 'sí', 'confirmar', 'confirmo'])

        # 2. BÚSQUEDA DE ALERTA (Más tolerante)
        # Buscamos alertas 'notified' para este usuario
        pending_alert = LowStockAlert.objects.filter(
            thread_id__contains=user_id[-9:], 
            status='notified'
        ).order_by('-created_at').first()

        if is_order_command or (pending_alert and is_confirmation):
            print(f"--- [ROUTER] Intención de pedido detectada: {user_msg} ---")
            
            # Extraer cantidad
            quantity_match = re.search(r'\d+', user_msg)
            quantity = int(quantity_match.group()) if quantity_match else None

            # Si tenemos alerta y cantidad -> ¡DISPARAMOS DETERMINÍSTICO!
            if pending_alert and quantity:
                print(f"--- [ROUTER] Ejecutando Pedido Determinista para {pending_alert.product_name} ---")
                from shopify_agent.agents.order_agent.tools import place_provider_order
                from shopify_agent.models import Provider

                provider = Provider.objects.filter(name__icontains=pending_alert.vendor).first() or Provider.objects.first()

                if provider and provider.email:
                    # PASAMOS EL user_id como thread_id para que la herramienta cierre la alerta en Supabase
                    result = place_provider_order.invoke({
                        "sku": pending_alert.sku,
                        "product_name": pending_alert.product_name,
                        "quantity": quantity,
                        "provider_email": provider.email,
                        "thread_id": user_id 
                    })
                    
                    if isinstance(result, dict) and result.get("action") == "send_himalaya_email":
                        return JsonResponse({
                            "status": "success",
                            "output": result.get("success_msg"),
                            "action": "reply_and_stop",
                            "himalaya_data": result
                        }, status=200)

            # 3. Si el router determinista no tiene info suficiente, DELEGAMOS AL AGENTE DE ÓRDENES
            print(f"--- [ROUTER] Delegando a Agente de Órdenes (LangGraph) para: {user_msg} ---")
            result = run_order_agent(user_msg, thread_id=user_id)
            
            response_data = {
                "status": "success",
                "output": result.get("agent_response"),
                "action": "reply_and_stop"
            }
            if result.get("himalaya_data"):
                response_data["himalaya_data"] = result.get("himalaya_data")
            
            return JsonResponse(response_data, status=200)

        # 4. Fallback para otros mensajes
        return JsonResponse({"status": "ignored", "output": ""})

    except Exception as e:
        print(f"--- [ROUTER ERROR] {e} ---")
        return JsonResponse({"error": str(e)}, status=500)
