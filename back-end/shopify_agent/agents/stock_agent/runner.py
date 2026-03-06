from shopify_agent.agents.stock_agent.graph import graph
from shopify_agent.agents.stock_agent.prompts import get_user_message
from shopify_agent.agents.stock_agent.dedupe import should_process
from shopify_agent.utils import get_shopify_product_details

def run_stock_agent(product_data: dict):
    """
    Orquestador principal del agente. Enriquecemos los datos si faltan.
    """
    print("\n--- [AGENTE] Iniciando procesamiento de payload ---")
    
    if not product_data or not isinstance(product_data, dict):
        print("[AGENTE] Error: Payload inválido")
        return {"status": "error", "reason": "Payload inválido o vacío"}

    # 1. Extraer IDs
    inv_id = product_data.get('inventory_item_id')
    product_id = product_data.get('id') or inv_id
    
    # 2. Extraer Stock
    stock_level = product_data.get('inventory_quantity')
    if stock_level is None:
        stock_level = product_data.get('available')
    
    if stock_level is None:
        print("[AGENTE] OMITIDO: No se detectó nivel de stock.")
        return {"status": "skipped", "reason": "No stock data"}

    # 3. FILTRO TEMPRANO (REGLA DE NEGOCIO) - Ahorro de Tokens
    if stock_level >= 5:
        print(f"[AGENTE] OMITIDO: Stock suficiente ({stock_level} >= 5)")
        return {"status": "skipped", "reason": f"Stock suficiente ({stock_level})"}

    # 4. ENRIQUECER PAYLOAD (Si falta el nombre)
    # Si viene de 'inventory_level/update', no trae nombre.
    if not product_data.get('title') and inv_id:
        print(f"[AGENTE] Enriqueciendo datos para inventory_item_id: {inv_id}...")
        details = get_shopify_product_details(inv_id)
        if details:
            product_data.update(details)
            print(f"[AGENTE] Datos recuperados: {details['title']} | SKU: {details['sku']}")

    # 5. DEDUPLICACIÓN
    if not should_process(str(product_id), stock_level):
        print(f"[AGENTE] OMITIDO: Alerta ya procesada recientemente para ID {product_id}")
        return {"status": "skipped", "reason": "Alerta ya procesada recientemente"}

    print("[AGENTE] Llamando a la IA (LangGraph)...")
    
    # 6. Preparación de inputs
    user_msg = get_user_message(product_data)
    
    # 7. Invocación del Grafo
    inputs = {"messages": [("user", user_msg)]}
    final_state = graph.invoke(inputs)
    
    ai_response = final_state["messages"][-1].content
    print(f"[AGENTE] Respuesta final de IA: {ai_response}")
    
    return {
        "status": "success",
        "agent_response": ai_response
    }
