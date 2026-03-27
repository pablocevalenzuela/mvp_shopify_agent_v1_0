from shopify_agent.agents.order_agent.graph import graph
from langchain_core.messages import ToolMessage
import json

def run_order_agent(message: str, thread_id: str):
    """
    Ejecuta el agente de pedidos para procesar la confirmación del usuario.
    """
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", message)]}
    
    final_state = graph.invoke(inputs, config=config)
    
    ai_response = final_state["messages"][-1].content
    himalaya_data = None

    # Buscamos en los mensajes si hubo una ejecución exitosa de la herramienta de pedido
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, ToolMessage):
            try:
                # El contenido puede venir como string o dict dependiendo del handler
                content = msg.content
                if isinstance(content, str):
                    try:
                        data = json.loads(content.replace("'", "\"")) # Limpieza básica si es repr
                    except:
                        continue
                else:
                    data = content
                
                if isinstance(data, dict) and data.get("action") == "send_himalaya_email":
                    himalaya_data = data
                    break
            except:
                continue

    return {
        "status": "success",
        "agent_response": ai_response,
        "himalaya_data": himalaya_data # <--- PASAMOS LA DATA AL VIEW
    }
