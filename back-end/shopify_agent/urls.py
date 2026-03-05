from django.urls import path
from shopify_agent.views import ShopifyWebhookView

urlpatterns = [
    path('webhook/shopify-stock/', ShopifyWebhookView.as_view(), name='shopify-webhook-stock'),
]
