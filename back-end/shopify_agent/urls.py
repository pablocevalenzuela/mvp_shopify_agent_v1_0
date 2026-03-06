from django.urls import path
from shopify_agent.views import shopify_webhook_receiver, openclaw_response_receiver

urlpatterns = [
    path('webhook/shopify-stock/', shopify_webhook_receiver, name='shopify-webhook-stock'),
    path('webhook/openclaw-response/', openclaw_response_receiver, name='openclaw-webhook-response'),
]
