from shopify_agent.agents.stock_agent.graph import graph
from shopify_agent.agents.stock_agent.prompts import get_user_message
from shopify_agent.utils import get_shopify_product_details
import os
import requests

def send_whatsapp_response(text: str, recipient_id: str):
    """
    Envía la respuesta final del agente al usuario por WhatsApp.
    """
    gateway_url = os.getenv('OPENCLAW_GATEWAY_URL')
    gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN')
    
    if gateway_url and gateway_token and recipient_id:
        clean_recipient = recipient_id.split('#')[0].strip()
        payload = {
            "tool": "message",
            "action": "send",
            "args": {"target": clean_recipient, "message": text, "channel": "whatsapp"}
        }
        headers = {"Authorization": f"Bearer {gateway_token}", "Content-Type": "application/json"}
        try:
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            print(f"--- [OPENCLAW DEBUG] Status: {response.status_code} | Response: {response.text} ---")
        except Exception as e:
            print(f"Error enviando respuesta a WhatsApp: {e}")

def run_stock_agent(data: dict, thread_id: str = "default"):
    """
    Orquestador del agente con soporte para hilos y envío de respuestas.
    """
    print(f"\n--- [AGENTE STOCK] Procesando Thread: {thread_id} ---")
    
    # 1. Enriquecimiento si viene de Shopify (Webhook)
    if 'inventory_item_id' in data and not data.get('title'):
        inv_id = data.get('inventory_item_id')
        details = get_shopify_product_details(inv_id)
        if details:
            data.update(details)

    # 2. Filtro de Stock (Solo para webhooks de Shopify)
    # Si es un mensaje de usuario (WhatsApp), saltamos este filtro
    is_shopify_webhook = 'inventory_item_id' in data
    stock_level = data.get('available') or data.get('inventory_quantity')
    
    if is_shopify_webhook and stock_level is not None and stock_level >= 5:
        return {"status": "skipped", "reason": "Stock suficiente"}

    # 3. Invocación del Grafo
    user_msg = get_user_message(data)
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", user_msg)]}
    
    final_state = graph.invoke(inputs, config=config)
    
    # 4. Enviar respuesta final al usuario (si hay texto)
    ai_message = final_state["messages"][-1]
    ai_response_text = ai_message.content

    # Si la respuesta tiene texto y no es solo una llamada a herramienta
    if ai_response_text:
        # Usamos thread_id como recipient_id (asumiendo que es el ID de WhatsApp)
        send_whatsapp_response(ai_response_text, thread_id)

    return {
        "status": "success",
        "agent_response": ai_response_text
    }
