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
    Gestiona comandos de Skills y respuestas de usuario para HITL.
    """
    print(f"\n--- [OPENCLAW RECEIVER] Recibiendo respuesta de WhatsApp ---")
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        # 1. Extracción y Normalización
        user_msg = (
            payload.get('body') or 
            payload.get('text') or 
            payload.get('message') or 
            payload.get('data', {}).get('content', '')
        )
        user_msg = user_msg.strip() if user_msg else ""
        
        user_id = (
            payload.get('bsuid') or 
            payload.get('sender_id') or 
            payload.get('sender') or 
            payload.get('from') or
            os.getenv('WHATSAPP_RECIPIENT_ID', 'default_user')
        )
        
        # Normalización CRÍTICA: Quitamos '+', espacios y convertimos a string
        # Esto asegura coincidencia con '56979250156' en la BD
        user_id = str(user_id).replace('+', '').replace(' ', '').strip()

        print(f"--- [ROUTER DEBUG] Msg: '{user_msg}' | User: {user_id} ---")

        # 2. Lógica Determinista (Confirmación de Pedido)
        user_msg_lower = user_msg.lower()
        is_confirmation = any(word in user_msg_lower for word in ['si', 'sí', 'confirmar', '/hacer_pedido', '/confirm_order'])

        # Buscamos la alerta 'notified' más reciente para este hilo
        pending_alert = LowStockAlert.objects.filter(
            thread_id=user_id,
            status='notified'
        ).order_by('-created_at').first()

        if pending_alert and is_confirmation:
            print(f"--- [ROUTER] Alerta detectada: {pending_alert.product_name} ---")
            
            # Intentar extraer cantidad del mensaje
            quantity_match = re.search(r'\d+', user_msg)
            quantity = int(quantity_match.group()) if quantity_match else None

            if quantity:
                print(f"--- [ROUTER] Cantidad detectada: {quantity}. Ejecutando Pedido... ---")
                from shopify_agent.agents.order_agent.tools import place_provider_order
                
                # Buscar proveedor asociado al vendor de la alerta
                provider = Provider.objects.filter(name__icontains=pending_alert.vendor).first() if pending_alert.vendor else Provider.objects.first()

                if provider and provider.email:
                    try:
                        result = place_provider_order.invoke({
                            "sku": pending_alert.sku,
                            "product_name": pending_alert.product_name,
                            "quantity": quantity,
                            "provider_email": provider.email
                        })
                        
                        # Marcamos como procesada para cerrar el ciclo
                        pending_alert.status = 'processed'
                        pending_alert.save()

                        # Si retorna el payload estructurado para Himalaya
                        if isinstance(result, dict) and result.get("action") == "send_himalaya_email":
                            return JsonResponse({
                                "status": "success",
                                "output": result.get("success_msg"),
                                "action": "reply_and_stop",
                                "himalaya_data": result,
                                "metadata": {"source": "deterministic_router"}
                            }, status=200)

                        return JsonResponse({
                            "status": "success",
                            "output": f"✅ {result}",
                            "action": "reply_and_stop"
                        }, status=200)
                    except Exception as tool_err:
                        print(f"--- [ROUTER ERROR] {tool_err} ---")
            
            # Si no hay cantidad, despertamos al Agente para que pregunte
            print(f"--- [ROUTER] Sin cantidad. Delegando al Agente de LangGraph ---")
            result = run_order_agent(user_msg, thread_id=user_id)
            return JsonResponse({
                "status": "order_flow_started",
                "output": result.get("agent_response"),
                "action": "reply_and_stop",
                "himalaya_data": result.get("himalaya_data")
            }, status=200)

        # 3. Fallback: Delegar todo lo demás al Agente LangGraph
        print(f"--- [ROUTER] Delegando a Agente LangGraph por defecto ---")
        result = run_order_agent(user_msg, thread_id=user_id)
        return JsonResponse({
            "status": "success",
            "output": result.get("agent_response", ""),
            "action": "reply_and_stop",
            "himalaya_data": result.get("himalaya_data")
        })

    except Exception as e:
        print(f"--- [ROUTER GLOBAL ERROR] {e} ---")
        return JsonResponse({"error": str(e)}, status=500)

    except Exception as e:
        print(f"--- [ROUTER GLOBAL ERROR] {e} ---")
        return JsonResponse({"error": str(e)}, status=500)
