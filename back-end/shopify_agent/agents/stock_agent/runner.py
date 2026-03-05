from shopify_agent.agents.stock_agent.graph import graph
from shopify_agent.agents.stock_agent.prompts import get_user_message
from shopify_agent.agents.stock_agent.dedupe import should_process

def run_stock_agent(product_data: dict):
    """
    Orquestador principal del agente.
    """
    product_id = product_data.get('id')
    stock_level = product_data.get('inventory_quantity', 0)
    
    # 1. Optimización: Filtro temprano (Rule-based)
    # Ahorramos tokens al no llamar al LLM si el stock es alto.
    if stock_level >= 5:
        return {"status": "skipped", "reason": "Stock suficiente (>=5)"}

    # 2. Optimización: Deduplicación
    # Evitamos re-notificar lo mismo y gastar tokens.
    if not should_process(str(product_id), stock_level):
        return {"status": "skipped", "reason": "Alerta ya procesada recientemente"}

    # 3. Preparación de inputs
    user_msg = get_user_message(product_data)
    
    # 4. Invocación del Grafo LangGraph
    # Usamos stream para recibir actualizaciones o invoke para resultado final.
    # El estado inicial solo lleva el mensaje necesario.
    inputs = {"messages": [("user", user_msg)]}
    
    # Ejecución
    final_state = graph.invoke(inputs)
    
    return {
        "status": "success",
        "agent_response": final_state["messages"][-1].content
    }
