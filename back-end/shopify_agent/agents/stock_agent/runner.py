from shopify_agent.agents.stock_agent.graph import graph
from shopify_agent.agents.stock_agent.prompts import get_user_message
from shopify_agent.agents.stock_agent.dedupe import should_process

def run_stock_agent(product_data: dict):
    """
    Orquestador principal del agente. Soporta Product Update e Inventory Update.
    """
    if not product_data or not isinstance(product_data, dict):
        return {"status": "error", "reason": "Payload inválido o vacío"}

    # Soporte para ambos esquemas de Shopify
    product_id = product_data.get('id') or product_data.get('inventory_item_id')
    
    # En Product Update es 'inventory_quantity', en Inventory Update es 'available'
    stock_level = product_data.get('inventory_quantity')
    if stock_level is None:
        stock_level = product_data.get('available', 0)
    
    # Si es un test de Shopify y no trae ID, le asignamos uno genérico para no fallar
    if not product_id:
        product_id = "test_product_id"

    # 1. Optimización: Filtro temprano (Rule-based)
    if stock_level >= 5:
        return {"status": "skipped", "reason": f"Stock suficiente ({stock_level})"}

    # 2. Optimización: Deduplicación
    if not should_process(str(product_id), stock_level):
        return {"status": "skipped", "reason": "Alerta ya procesada recientemente"}

    # 3. Preparación de inputs
    user_msg = get_user_message(product_data)
    
    # 4. Invocación del Grafo LangGraph
    inputs = {"messages": [("user", user_msg)]}
    final_state = graph.invoke(inputs)
    
    return {
        "status": "success",
        "agent_response": final_state["messages"][-1].content
    }
