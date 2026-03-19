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
    Compatible con OpenClaw v2026.3.13 (BSUID y nuevos esquemas de payload).
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        # OpenClaw v2026.3.13: texto en 'text', 'message' o 'data.content'
        user_msg = (
            payload.get('text') or 
            payload.get('message') or 
            payload.get('data', {}).get('content', '')
        )
        user_msg = user_msg.strip()
        
        # Identificador único del usuario (Thread ID)
        user_id = (
            payload.get('bsuid') or 
            payload.get('sender_id') or 
            payload.get('sender') or 
            payload.get('from')
        )
        
        if not user_id:
            user_id = (
                payload.get('data', {}).get('sender_id') or 
                payload.get('context', {}).get('user_id')
            )
            
        if not user_id:
            user_id = os.getenv('WHATSAPP_RECIPIENT_ID', 'default_user')

        if not user_msg:
            return JsonResponse({"status": "no text content"}, status=200)

        # 1. Prioridad: Comandos de Skill (OpenClaw -> Backend)
        skill_id = payload.get('skill_id') or payload.get('id') or payload.get('data', {}).get('skill_id')
        
        # Caso A: Solicitud directa de inventario
        if skill_id == 'request_product' or '@solicitar_productos' in user_msg.lower():
            print(f"--- [ROUTER] Skill request_product detectada para {user_id} ---")
            result = run_stock_agent({"text": user_msg}, thread_id=user_id)
            return JsonResponse({"status": "skill_triggered", "agent": "stock_agent"})

        # Caso B: Confirmación de pedido (Activada por Skill o por texto "SI")
        has_pending_stock_alert = LowStockAlert.objects.filter(
            thread_id=user_id, 
            status='notified'
        ).exists()

        if skill_id == 'confirm_order_skill' or (has_pending_stock_alert and user_msg.lower() in ['si', 'sí', 's']):
            print(f"--- [ROUTER] Iniciando flujo de pedido con OrderAgent para {user_id} ---")
            result = run_order_agent(user_msg, thread_id=user_id)
            
            # Si el agente respondió, enviamos esa respuesta a través de OpenClaw
            from shopify_agent.agents.stock_agent.runner import send_whatsapp_response
            send_whatsapp_response(result.get("agent_response", "Procesando pedido..."), user_id)
            
            return JsonResponse({
                "status": "order_flow_started", 
                "agent_response": result.get("agent_response")
            })

        # 2. Lógica de Enrutamiento para respuestas HITL genéricas:
        if has_pending_stock_alert or any(word in user_msg.lower() for word in ['proveedor', 'sku', 'no', 'unidades']):
            print(f"--- [ROUTER] Enrutando a StockAgent para flujo de stock ({user_id}) ---")
            result = run_stock_agent({"text": user_msg}, thread_id=user_id)
            
            if user_msg.lower() == 'no':
                LowStockAlert.objects.filter(thread_id=user_id, status='notified').update(status='ignored')
                
        else:
            # Por defecto, otras consultas van al OrderAgent
            print(f"--- [ROUTER] Enrutando a OrderAgent por defecto para {user_id} ---")
            result = run_order_agent(user_msg, thread_id=user_id)

        return JsonResponse({"status": "success"})

    except Exception as e:
        print(f"Error en OpenClaw Router: {e}")
        return JsonResponse({"error": str(e)}, status=500)
