import hmac
import hashlib
import json
import base64
import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from shopify_agent.agents.stock_agent.runner import run_stock_agent

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
        if payload is None:
            payload = {"inventory_item_id": "test_item_99", "available": 2, "title": "Test", "sku": "SKU-001"}

        # Usamos el número de WhatsApp configurado como thread_id por defecto para alertas
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
    Configurar este endpoint como 'Outbound URL' en OpenClaw.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        # OpenClaw Universal IM suele enviar: {"from": "ID", "text": "mensaje", "channel": "whatsapp"}
        # Ajustar según el formato exacto que veas en tus logs de OpenClaw.
        user_msg = payload.get('text')
        user_id = payload.get('from') or payload.get('to') # Depende de la dirección

        if not user_msg:
            return JsonResponse({"status": "no text"}, status=200)

        # Procesar con el agente usando el user_id como hilo para mantener el contexto
        result = run_stock_agent({"text": user_msg}, thread_id=user_id)
        
        # Enviar la respuesta de la IA de vuelta a WhatsApp vía OpenClaw
        gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
        gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
        
        if gateway_url and gateway_token:
            out_payload = {
                "tool": "message",
                "action": "send",
                "args": {
                    "target": user_id,
                    "message": result["agent_response"],
                    "channel": "whatsapp"
                }
            }
            requests.post(gateway_url, json=out_payload, headers={"Authorization": f"Bearer {gateway_token}"})

        return JsonResponse({"status": "processed"})
    except Exception as e:
        print(f"Error OpenClaw Receiver: {e}")
        return JsonResponse({"error": str(e)}, status=500)
