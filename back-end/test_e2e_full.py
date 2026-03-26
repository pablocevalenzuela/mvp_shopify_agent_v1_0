import os
import django

# 1. Configurar el entorno (DEBE SER LO PRIMERO)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.develop')
django.setup()

# 2. Ahora sí podemos importar modelos y lógica
import re
from shopify_agent.agents.stock_agent.runner import run_stock_agent
from shopify_agent.agents.order_agent.tools import place_provider_order
from shopify_agent.models import LowStockAlert, Provider, ProviderOrder

# --- CONFIGURACIÓN DEL TEST ---
TEST_SKU = "SKU-PRO-E2E"
TEST_PRODUCT = "Queso Emmental E2E"
TEST_VENDOR = "ModaGlobal"
TEST_EMAIL = "pablo@example.com" # Cambia esto para recibir el correo real
USER_REPLY = "si y 150" 
THREAD_ID = os.getenv('WHATSAPP_RECIPIENT_ID', '56979250156')

def run_test():
    print(f"\n🚀 === INICIANDO TEST E2E: {TEST_PRODUCT} ===\n")

    # 1. PREPARACIÓN: Proveedor
    provider, created = Provider.objects.get_or_create(
        name=TEST_VENDOR, 
        defaults={"email": TEST_EMAIL, "contact_person": "Gerente de Ventas"}
    )
    if not created:
        provider.email = TEST_EMAIL
        provider.save()
    print(f"✅ Proveedor listo: {provider.name} ({provider.email})")

    # 2. SIMULACIÓN: Webhook de Shopify
    print(f"\n[PASO 1] Recibiendo Webhook de Shopify (Stock: 2 unidades)...")
    mock_webhook = {
        "inventory_item_id": 123456789,
        "available": 2,
        "sku": TEST_SKU,
        "title": TEST_PRODUCT,
        "vendor": TEST_VENDOR
    }
    result_stock = run_stock_agent(mock_webhook, thread_id=THREAD_ID)
    print(f"📡 Resultado Alerta: {result_stock.get('status')}")

    # 3. PROCESAMIENTO: Respuesta de usuario
    print(f"\n[PASO 2] Procesando respuesta del usuario: '{USER_REPLY}'")
    alert = LowStockAlert.objects.filter(thread_id=THREAD_ID, status='notified').order_by('-created_at').first()

    if alert:
        quantity_match = re.search(r'\d+', USER_REPLY)
        quantity = int(quantity_match.group()) if quantity_match else 0
        
        if quantity > 0:
            print(f"📦 Cantidad detectada: {quantity}. Ejecutando pedido...")
            
            # 4. EJECUCIÓN: Skill Himalaya
            print(f"\n[PASO 3] Llamando a la Skill Himalaya en OpenClaw...")
            result_himalaya = place_provider_order.invoke({
                "sku": alert.sku,
                "product_name": alert.product_name,
                "quantity": quantity,
                "provider_email": provider.email
            })
            
            # 5. VALIDACIÓN FINAL
            order_exists = ProviderOrder.objects.filter(sku=TEST_SKU, quantity=quantity).exists()
            
            print(f"\n🏁 === RESUMEN DEL TEST E2E ===")
            print(f"Result HIMALAYA: {result_himalaya}")
            print(f"Orden grabada en DB: {'SÍ' if order_exists else 'NO'}")
            
            if "Pedido de" in str(result_himalaya) or "enviado exitosamente" in str(result_himalaya):
                print(f"\n✨ ¡TEST EXITOSO! El sistema ha completado todo el ciclo.")
            else:
                print(f"\n❌ EL TEST FALLÓ: Revisa la respuesta de OpenClaw arriba.")
        else:
            print("❌ Error: No se pudo extraer la cantidad.")
    else:
        print("❌ Error: No se encontró la alerta de stock bajo.")

if __name__ == "__main__":
    run_test()
