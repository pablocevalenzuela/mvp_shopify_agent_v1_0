from shopify_agent.agents.stock_agent.graph import graph
from shopify_agent.agents.stock_agent.prompts import get_user_message
from shopify_agent.agents.stock_agent.dedupe import should_process
from shopify_agent.utils import get_shopify_product_details
import os

def run_stock_agent(data: dict, thread_id: str = "default"):
    """
    Orquestador del agente con soporte para hilos de conversación.
    """
    print(f"\n--- [AGENTE] Procesando para Thread: {thread_id} ---")
    
    # 1. Enriquecimiento si viene de Shopify
    if 'inventory_item_id' in data and not data.get('title'):
        inv_id = data.get('inventory_item_id')
        details = get_shopify_product_details(inv_id)
        if details:
            data.update(details)

    # 2. Filtro Temprano por Stock (Solo para actualizaciones de Shopify)
    stock_level = data.get('available') or data.get('inventory_quantity')
    if stock_level is not None and stock_level >= 5:
        return {"status": "skipped", "reason": "Stock suficiente"}

    # 3. Preparación de inputs
    user_msg = get_user_message(data)
    
    # 4. Invocación del Grafo con Persistencia (Config)
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", user_msg)]}
    
    final_state = graph.invoke(inputs, config=config)
    
    ai_response = final_state["messages"][-1].content
    return {
        "status": "success",
        "agent_response": ai_response
    }
