from shopify_agent.agents.stock_agent.graph import graph
from shopify_agent.agents.stock_agent.prompts import get_user_message
from shopify_agent.agents.stock_agent.dedupe import should_process

def run_stock_agent(product_data: dict):
    """
    Orquestador principal del agente. Soporta Product Update e Inventory Update.
    """
    print("\n--- [AGENTE] Iniciando procesamiento de payload ---")
    
    if not product_data or not isinstance(product_data, dict):
        print("[AGENTE] Error: Payload inválido")
        return {"status": "error", "reason": "Payload inválido o vacío"}

    # Soporte para ambos esquemas de Shopify
    product_id = product_data.get('id') or product_data.get('inventory_item_id')
    
    # IMPORTANTE: En webhooks reales de Inventory Level, el stock viene en 'available'
    stock_level = product_data.get('inventory_quantity')
    if stock_level is None:
        stock_level = product_data.get('available')
        
    # Si sigue siendo None, es que el campo tiene otro nombre o no viene
    if stock_level is None:
        print(f"[AGENTE] Advertencia: No se encontró nivel de stock en el payload. Campos: {list(product_data.keys())}")
        stock_level = 0
    
    print(f"[AGENTE] Producto ID: {product_id} | Stock detectado: {stock_level}")

    # 1. Optimización: Filtro temprano (Rule-based)
    if stock_level >= 5:
        print(f"[AGENTE] OMITIDO: Stock suficiente ({stock_level} >= 5)")
        return {"status": "skipped", "reason": f"Stock suficiente ({stock_level})"}

    # 2. Optimización: Deduplicación
    if not should_process(str(product_id), stock_level):
        print(f"[AGENTE] OMITIDO: Alerta ya procesada recientemente para ID {product_id}")
        return {"status": "skipped", "reason": "Alerta ya procesada recientemente"}

    print("[AGENTE] Llamando a la IA (LangGraph)...")
    
    # 3. Preparación de inputs
    user_msg = get_user_message(product_data)
    
    # 4. Invocación del Grafo LangGraph
    inputs = {"messages": [("user", user_msg)]}
    final_state = graph.invoke(inputs)
    
    ai_response = final_state["messages"][-1].content
    print(f"[AGENTE] Respuesta final de IA: {ai_response}")
    
    return {
        "status": "success",
        "agent_response": ai_response
    }
