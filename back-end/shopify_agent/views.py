from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from shopify_agent.agents.stock_agent.runner import run_stock_agent

class ShopifyWebhookView(APIView):
    """
    Endpoint para recibir webhooks de Shopify (Product/Update o Inventory/Update).
    """
    def post(self, request, *args, **kwargs):
        # Datos recibidos de Shopify
        # Nota: En producción deberías validar el HMAC para seguridad
        product_data = request.data
        
        # Ejecutamos el agente de IA (con sus filtros de optimización internos)
        try:
            result = run_stock_agent(product_data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
