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
        
        # Identificar el mensaje
        user_msg = (
            payload.get('body') or 
            payload.get('text') or 
            payload.get('message') or 
            payload.get('data', {}).get('content', '')
        )
        user_msg = user_msg.strip() if user_msg else ""
        
        # Identificar al usuario
        user_id = (
            payload.get('bsuid') or 
            payload.get('sender_id') or 
            payload.get('sender') or 
            payload.get('from') or
            os.getenv('WHATSAPP_RECIPIENT_ID', 'default_user')
        )

        print(f"--- [ROUTER DEBUG] Msg: '{user_msg}' | User: {user_id} ---")

        # 1. Comandos directos o confirmación de pedido (Determinista)
        user_msg_lower = user_msg.lower()
        is_confirmation = any(word in user_msg_lower for word in ['si', 'sí', 'confirmar', '/hacer_pedido', '/confirm_order'])

        has_pending_stock_alert = LowStockAlert.objects.filter(
            thread_id=user_id,
            status='notified'
        ).exists()

        if has_pending_stock_alert and is_confirmation:
            print(f"--- [ROUTER] Confirmación detectada. Buscando alerta reciente... ---")
            alert = LowStockAlert.objects.filter(
                thread_id=user_id, status='notified').order_by('-created_at').first()

            if alert:
                # Extraer cantidad (prioridad a números en el mensaje)
                quantity_match = re.search(r'\d+', user_msg)
                quantity = int(quantity_match.group()) if quantity_match else None

                if quantity:
                    print(f"--- [ROUTER] Cantidad detectada: {quantity}. Ejecutando pedido directo... ---")
                    from shopify_agent.agents.order_agent.tools import place_provider_order
                    from shopify_agent.models import Provider

                    # Buscar proveedor
                    provider = Provider.objects.filter(name__icontains=alert.vendor).first() if alert.vendor else Provider.objects.first()

                    if provider and provider.email:
                        print(f"--- [ROUTER] Proveedor hallado: {provider.email} ---")
                        try:
                            result = place_provider_order.invoke({
                                "sku": alert.sku,
                                "product_name": alert.product_name,
                                "quantity": quantity,
                                "provider_email": provider.email
                            })
                            
                            # Marcamos la alerta como procesada
                            alert.status = 'processed'
                            alert.save()

                            # Si el resultado es el diccionario de instrucción para Himalaya
                            if isinstance(result, dict) and result.get("action") == "send_himalaya_email":
                                return JsonResponse({
                                    "status": "success",
                                    "output": result.get("success_msg", "Pedido procesado correctamente."),
                                    "action": "reply_and_stop",
                                    "himalaya_data": result,  # <--- PAYLOAD PARA OPENCLAW
                                    "metadata": {"source": "deterministic_router_himalaya"}
                                }, status=200)

                            return JsonResponse({
                                "status": "success",
                                "output": f"✅ {result}",
                                "action": "reply_and_stop"
                            }, status=200)
                        except Exception as tool_err:
                            print(f"--- [ROUTER ERROR] Error en place_provider_order: {tool_err} ---")
            
            # Si no hay cantidad, despertamos al Agente para que pregunte
            print(f"--- [ROUTER] No se halló cantidad o alerta. Fallback al OrderAgent ---")
            result = run_order_agent(user_msg, thread_id=user_id)
            
            response_data = {
                "status": "order_flow_started_fallback",
                "output": result.get("agent_response", "Procesando pedido..."),
                "action": "reply_and_stop"
            }
            if result.get("himalaya_data"):
                response_data["himalaya_data"] = result.get("himalaya_data")
                
            return JsonResponse(response_data, status=200)

        # 2. Respuestas HITL genéricas (No, otros comandos)
        if any(word in user_msg_lower for word in ['no', 'ignorar', 'cancelar']):
            print(f"--- [ROUTER] Usuario ignoró la alerta ---")
            LowStockAlert.objects.filter(thread_id=user_id, status='notified').update(status='ignored')
            return JsonResponse({"status": "ignored", "action": "reply_and_stop", "output": "De acuerdo, he ignorado la alerta."})

        # 3. Default: Delegar al OrderAgent
        print(f"--- [ROUTER] Delegando a OrderAgent por defecto ---")
        result = run_order_agent(user_msg, thread_id=user_id)
        
        response_data = {
            "status": "success",
            "output": result.get("agent_response", ""),
            "action": "reply_and_stop"
        }
        if result.get("himalaya_data"):
            response_data["himalaya_data"] = result.get("himalaya_data")

        return JsonResponse(response_data)

    except Exception as e:
        print(f"--- [ROUTER GLOBAL ERROR] {e} ---")
        return JsonResponse({"error": str(e)}, status=500)
