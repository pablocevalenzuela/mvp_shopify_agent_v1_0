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
    """
    Webhook de Inventario de Shopify: Dispara alertas de bajo stock.
    """
    try:
        request_body = request.body
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')
        if not hmac_header or not verify_shopify_webhook(request_body, hmac_header):
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        payload = json.loads(request_body.decode('utf-8'))
        
        # Enviamos la alerta al número configurado por defecto
        thread_id = os.getenv('WHATSAPP_RECIPIENT_ID', 'shopify_admin')
        result = run_stock_agent(payload, thread_id=thread_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def openclaw_response_receiver(request):
    """
    RECEPTOR PRINCIPAL DE OPENCLAW (WHATSAPP).
    Gestiona comandos de Skills y respuestas de usuario para HITL.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        user_msg = payload.get('text') or payload.get('message', '')
        user_msg = user_msg.strip()
        
        # Identificador único del usuario de WhatsApp (Thread ID)
        user_id = payload.get('from') or payload.get('sender') or payload.get('sender_id')
        
        if not user_id:
            user_id = os.getenv('WHATSAPP_RECIPIENT_ID', 'default_user')

        if not user_msg:
            return JsonResponse({"status": "no text"}, status=200)

        # 1. Prioridad: Comando de Skill o ID de Skill 'request_product'
        skill_id = payload.get('skill_id') or payload.get('id')
        if skill_id == 'request_product' or '@solicitar_productos' in user_msg.lower():
            print(f"--- [ROUTER] Skill request_product detectada para {user_id} ---")
            result = run_stock_agent({"text": user_msg}, thread_id=user_id)
            return JsonResponse({"status": "skill_triggered", "agent": "stock_agent"})

        # 2. Lógica de Enrutamiento para respuestas HITL:
        # Verificamos si hay una alerta de stock bajo pendiente para este usuario
        has_pending_stock_alert = LowStockAlert.objects.filter(
            thread_id=user_id, 
            status='notified'
        ).exists()

        # Si el usuario responde a una alerta o está en medio de un flujo de stock
        if has_pending_stock_alert or any(word in user_msg.lower() for word in ['si', 'no', 'proveedor', 'sku']):
            print(f"--- [ROUTER] Enrutando a StockAgent para flujo de reposición ({user_id}) ---")
            result = run_stock_agent({"text": user_msg}, thread_id=user_id)
            
            # Si el usuario confirma un pedido de stock, podemos marcar la alerta como procesada
            if "pedido enviado" in result.get("agent_response", "").lower():
                LowStockAlert.objects.filter(thread_id=user_id, status='notified').update(status='processed')
            elif user_msg.lower() == 'no':
                LowStockAlert.objects.filter(thread_id=user_id, status='notified').update(status='ignored')
                
        else:
            # Por defecto, si no es flujo de stock, podría ser el OrderAgent (u otro)
            print(f"--- [ROUTER] Enrutando a OrderAgent por defecto para {user_id} ---")
            # Suponiendo que run_order_agent maneja otros tipos de solicitudes (ej: info de pedidos)
            result = run_order_agent(user_msg, thread_id=user_id)

        return JsonResponse({"status": "success"})

    except Exception as e:
        print(f"Error en OpenClaw Router: {e}")
        return JsonResponse({"error": str(e)}, status=500)
