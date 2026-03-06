from shopify_agent.agents.order_agent.graph import graph

def run_order_agent(message: str, thread_id: str):
    """
    Ejecuta el agente de pedidos para procesar la confirmación del usuario.
    """
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", message)]}
    
    final_state = graph.invoke(inputs, config=config)
    
    ai_response = final_state["messages"][-1].content
    return {
        "status": "success",
        "agent_response": ai_response
    }
