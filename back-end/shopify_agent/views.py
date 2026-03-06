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
    """
    Verifica la firma HMAC del webhook de Shopify.
    Copiado de la implementación exitosa compartida por el usuario.
    """
    # Intentamos obtenerlo de settings o de variable de entorno directamente
    secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')
    if not secret:
        print("ADVERTENCIA: SHOPIFY_WEBHOOK_SECRET no está configurado.")
        return False
        
    secret = secret.encode('utf-8')
    # Calcular el digest en bytes y luego codificar en Base64
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
    Recibe y procesa los webhooks de Shopify utilizando el agente de IA.
    """
    if request.method != 'POST':
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        request_body = request.body
        # Shopify envía el header con este nombre exacto
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256')

        if not hmac_header:
            print("Error: Falta el header X-Shopify-Hmac-SHA256")
            return JsonResponse(
                {'error': 'Missing HMAC header'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not verify_shopify_webhook(request_body, hmac_header):
            print("Error: Firma HMAC inválida")
            return JsonResponse(
                {'error': 'Invalid HMAC signature'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Parsear el payload
        payload = json.loads(request_body.decode('utf-8'))
        
        print("--- Payload Recibido ---")
        # print(json.dumps(payload, indent=2)) # Opcional: para debug pesado

        # Ejecutar el Agente de IA con el patrón ReAct
        result = run_stock_agent(payload)

        return JsonResponse(
            {
                'message': 'Webhook processed',
                'agent_result': result
            },
            status=status.HTTP_200_OK
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON payload'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        print(f"Error procesando el webhook de Shopify: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': 'Internal server error', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
