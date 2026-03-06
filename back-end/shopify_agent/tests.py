import json
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase

from shopify_agent.agents.stock_agent.runner import run_stock_agent

class StockAgentLogicTests(TestCase):
    """
    Pruebas unitarias para la lógica del agente de stock (runner.py).
    """
    
    @patch('shopify_agent.agents.stock_agent.runner.should_process', return_value=True)
    def test_run_stock_agent_skips_high_stock(self, mock_dedupe):
        """
        Debe omitir la ejecución si el stock es >= 5 (Optimización de tokens).
        """
        payload = {"id": "123", "inventory_quantity": 10}
        result = run_stock_agent(payload)
        
        self.assertEqual(result['status'], 'skipped')
        self.assertIn("Stock suficiente", result['reason'])

    @patch('shopify_agent.agents.stock_agent.runner.graph.invoke')
    @patch('shopify_agent.agents.stock_agent.runner.should_process', return_value=True)
    def test_run_stock_agent_calls_llm_on_low_stock(self, mock_dedupe, mock_graph):
        """
        Debe llamar al grafo de IA si el stock es < 5.
        """
        # Simulamos respuesta del grafo de LangGraph
        mock_graph.return_value = {
            "messages": [MagicMock(content="Alerta enviada correctamente")]
        }
        
        payload = {"id": "123", "inventory_quantity": 2, "title": "Test Product"}
        result = run_stock_agent(payload)
        
        self.assertEqual(result['status'], 'success')
        mock_graph.assert_called_once()

class ShopifyWebhookIntegrationTests(APITestCase):
    """
    Pruebas de integración para el endpoint del Webhook.
    """
    
    def setUp(self):
        self.url = reverse('shopify-webhook-stock')
        # Configuramos un secreto de prueba en el entorno
        import os
        os.environ['SHOPIFY_WEBHOOK_SECRET'] = 'test_secret'

    @patch('shopify_agent.views.verify_shopify_webhook', return_value=True)
    @patch('shopify_agent.views.run_stock_agent')
    def test_webhook_receives_data_correctly(self, mock_runner, mock_verify):
        """
        Simula un POST exitoso de Shopify (con HMAC verificado).
        """
        mock_runner.return_value = {"status": "success", "agent_response": "OK"}
        
        payload = {"id": "999", "available": 1}
        # Simulamos los headers que enviaría Shopify
        headers = {'HTTP_X_SHOPIFY_HMAC_SHA256': 'fake_hmac'}
        
        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Webhook processed successfully', response.data['message'])

    def test_webhook_rejects_unauthorized(self):
        """
        Debe rechazar peticiones sin HMAC o con HMAC inválido (401).
        """
        response = self.client.post(self.url, data={"id": "1"}, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
