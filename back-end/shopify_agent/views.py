import hmac
import hashlib
import json
import base64
import os
import requests
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
    if not secret: return False
    secret = secret.encode('utf-8')
    digest = base64.b64encode(hmac.new(secret, data, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(digest, hmac_header)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_webhook_receiver(request):
    try:
        request_body = request.body
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')
        if not hmac_header or not verify_shopify_webhook(request_body, hmac_header):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        payload = json.loads(request_body.decode('utf-8'))
        thread_id = os.getenv('WHATSAPP_RECIPIENT_ID', 'shopify_admin')
        result = run_stock_agent(payload, thread_id=thread_id)
        return JsonResponse(result)
    except Exception as e:
        print(f"--- [WEBHOOK ERROR] {e} ---")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def openclaw_response_receiver(request):
    """
    RECEPTOR PRINCIPAL DE OPENCLAW (WHATSAPP).
    Diseñado para interceptar respuestas deterministas y evitar el uso de LLM (Error 402).
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        print(f"--- [ROUTER DEBUG] Payload: {json.dumps(payload)} ---")
        
        # Reconocer 'body' de OpenClaw v2026.3.13
        user_msg = payload.get('body') or payload.get('text') or payload.get('message', '')
        user_msg = user_msg.strip() if user_msg else ""
        
        user_id = payload.get('sender_id') or payload.get('from') or payload.get('sender', 'default')
        
        # 1. Detección de Confirmación Determinista
        is_confirmation = any(word in user_msg.lower() for word in ['si', 'sí', 's', 'confirmar', '/confirm_order'])
        
        if is_confirmation:
            print(f"--- [ROUTER] Intento de procesamiento determinista para {user_id} ---")
            # Buscar alerta pendiente
            alert = LowStockAlert.objects.filter(status='notified').order_by('-created_at').first()
            
            if alert:
                from shopify_agent.agents.order_agent.tools import place_provider_order
                provider = Provider.objects.filter(name__icontains=alert.vendor).first() if alert.vendor else Provider.objects.first()
                
                if provider and provider.email:
                    print(f"--- [ROUTER] Ejecutando envío directo a {provider.email} ---")

                    return JsonResponse({
                        "status": "ok",
                        "recipient": provider.email,
                        "sku": alert.sku,
                        "product": alert.product_name,
                        "quantity": 10
                        }, status=200)
                    """
                    result_msg = place_provider_order.invoke({
                        "sku": alert.sku,
                        "product_name": alert.product_name,
                        "quantity": 10,
                        "provider_email": provider.email
                    })
                    
                    
                    return JsonResponse({
                        "status": "success",
                        "output": f"✅ {result_msg}",
                        "action": "stop",
                        "reply": f"✅ {result_msg}"
                    }, status=200)
                """

        # 2. Si no es confirmación, intentar con el Agente (solo si hay créditos)
        # o devolver un error controlado si sabemos que no hay créditos.
        print(f"--- [ROUTER] Mensaje no procesado determinísticamente: {user_msg} ---")
        return JsonResponse({"status": "ignored", "action": "continue"}, status=200)

    except Exception as e:
        print(f"--- [ROUTER ERROR] {e} ---")
        return JsonResponse({"error": str(e)}, status=500)
