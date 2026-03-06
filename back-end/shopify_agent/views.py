import hmac
import hashlib
import base64
import json
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from shopify_agent.agents.stock_agent.runner import run_stock_agent

class ShopifyWebhookView(APIView):
    """
    Endpoint para recibir webhooks de Shopify con validación HMAC.
    """
    def post(self, request, *args, **kwargs):
        # 1. Obtener el secreto desde las variables de entorno
        webhook_secret = os.getenv('SHOPIFY_WEBHOOK_SECRET')
        
        # 2. Obtener el HMAC enviado por Shopify en los headers
        shopify_hmac = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256')
        
        # 3. Leer el cuerpo de la petición (raw data) para la verificación
        data = request.body
        
        if webhook_secret and shopify_hmac:
            # Calcular el HMAC localmente
            hash = hmac.new(webhook_secret.encode('utf-8'), data, hashlib.sha256)
            generated_hmac = base64.b64encode(hash.digest()).decode('utf-8')
            
            # Comparar (usando compare_digest para evitar ataques de tiempo)
            if not hmac.compare_digest(generated_hmac, shopify_hmac):
                return Response({"error": "Invalid HMAC signature"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # 4. Si la validación pasa (o no hay secreto configurado aún), procesar
        try:
            # Convertimos el body a JSON para el agente
            product_data = json.loads(data)
            result = run_stock_agent(product_data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            # IMPRIMIR EL ERROR PARA DIAGNÓSTICO
            print(f"--- ERROR EN WEBHOOK ---")
            print(str(e))
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
