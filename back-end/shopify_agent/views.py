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
from shopify_agent.models import LowStockAlert

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
    """Webhook de Inventario de Shopify."""
    try:
        request_body = request.body
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')
        if not hmac_header or not verify_shopify_webhook(request_body, hmac_header):
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        payload = json.loads(request_body.decode('utf-8'))
        
        # El thread_id es el número configurado para recibir alertas
        thread_id = os.getenv('WHATSAPP_RECIPIENT_ID', 'shopify_alerts')
        result = run_stock_agent(payload, thread_id=thread_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def openclaw_response_receiver(request):
    """
    RECIBE RESPUESTAS DE WHATSAPP VÍA OPENCLAW.
    Enruta al Agente de Pedidos si hay una alerta pendiente.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        user_msg = payload.get('text', '').strip()
        user_id = payload.get('from') or payload.get('to') or os.getenv('WHATSAPP_RECIPIENT_ID')

        if not user_msg:
            return JsonResponse({"status": "no text"}, status=200)

        # Lógica de Enrutamiento:
        # Si el usuario dice "SÍ" o tenemos una alerta reciente sin procesar, usamos OrderAgent
        has_pending_alert = LowStockAlert.objects.filter(thread_id=user_id, status='notified').exists()
        
        if has_pending_alert or user_msg.lower() in ['si', 'sí', 'ok', 'vale', 'adelante']:
            print(f"--- [Router] Enrutando a OrderAgent para {user_id} ---")
            result = run_order_agent(user_msg, thread_id=user_id)
        else:
            print(f"--- [Router] Enrutando a StockAgent para {user_id} ---")
            result = run_stock_agent({"text": user_msg}, thread_id=user_id)
        
        # Enviar la respuesta de la IA de vuelta a WhatsApp vía OpenClaw
        gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
        gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
        
        if gateway_url and gateway_token and result.get("agent_response"):
            out_payload = {
                "tool": "message",
                "action": "send",
                "args": {
                    "target": user_id,
                    "message": result["agent_response"],
                    "channel": "whatsapp"
                }
            }
            requests.post(gateway_url, json=out_payload, headers={"Authorization": f"Bearer {gateway_token}"}, timeout=15)

        return JsonResponse({"status": "processed"})
    except Exception as e:
        print(f"Error OpenClaw Receiver: {e}")
        return JsonResponse({"error": str(e)}, status=500)
