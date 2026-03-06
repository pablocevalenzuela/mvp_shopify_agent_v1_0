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

# REACTIVADO PARA PROCESAR EL WEBHOOK
from shopify_agent.agents.stock_agent.runner import run_stock_agent

def verify_shopify_webhook(data, hmac_header):
    secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')
    if not secret:
        print("ADVERTENCIA: SHOPIFY_WEBHOOK_SECRET no está configurado.")
        return False
    secret = secret.encode('utf-8')
    digest = base64.b64encode(
        hmac.new(secret, data, hashlib.sha256).digest()).decode()
    
    print("--- Verificación de Webhook Shopify ---")
    print(f"HMAC de Shopify: {hmac_header}")
    print(f"Digest Calculado: {digest}")
    
    return hmac.compare_digest(digest, hmac_header)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def shopify_webhook_receiver(request):
    """
    Recibe webhooks de Shopify, valida la firma y ejecuta el agente de IA.
    """
    if request.method != 'POST':
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        request_body = request.body
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')

        if not hmac_header:
            return JsonResponse({'error': 'Missing HMAC header'}, status=401)

        if not verify_shopify_webhook(request_body, hmac_header):
            return JsonResponse({'error': 'Invalid HMAC signature'}, status=401)

        raw_body = request_body.decode('utf-8')
        payload = json.loads(raw_body)
        
        # MANEJO DE TEST VACÍO (NULL)
        if payload is None:
            print("INFO: Shopify envió un test vacío (null). Usando datos de prueba.")
            payload = {
                "inventory_item_id": "test_item_99",
                "available": 2, # Forzamos alerta para probar la IA
                "title": "Producto de Prueba (Shopify Test)",
                "sku": "SKU-TEST-001"
            }

        print("--- PROCESANDO CON AGENTE IA ---")
        result = run_stock_agent(payload)

        return JsonResponse({
            'message': 'Webhook processed successfully',
            'agent_result': result
        }, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
