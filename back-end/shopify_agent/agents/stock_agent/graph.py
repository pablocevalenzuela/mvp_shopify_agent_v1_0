import os
from typing import Literal
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from shopify_agent.agents.stock_agent.state import AgentState
from shopify_agent.agents.stock_agent.tools import send_stock_alert
from shopify_agent.agents.stock_agent.prompts import SYSTEM_PROMPT

# 1. Definir herramientas y el nodo de herramientas
tools = [send_stock_alert]
tool_node = ToolNode(tools)

# 2. Configurar el LLM con los parámetros de GitHub Models
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("GITHUB_TOKEN"),
    base_url="https://models.inference.ai.azure.com",
    temperature=0,
    max_tokens=1000
).bind_tools(tools)

# 3. Definir los nodos del Grafo
def call_model(state: AgentState):
    """
    Nodo que llama al LLM. 
    Inyecta el SYSTEM_PROMPT y pasa el historial de mensajes.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    # Devolvemos la actualización del estado (mensajes)
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", END]:
    """
    Lógica de control para decidir si seguir con herramientas o terminar.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # Si el LLM solicitó usar una herramienta
    if last_message.tool_calls:
        return "tools"
    
    # Si no hay herramientas, terminamos
    return END

# 4. Construcción explícita del Grafo (Patrón ReAct)
workflow = StateGraph(AgentState)

# Agregar nodos
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Definir el flujo (Edges)
workflow.add_edge(START, "agent")

# Edge condicional después de llamar al agente
workflow.add_conditional_edges(
    "agent",
    should_continue,
)

# El nodo de herramientas siempre vuelve al agente para procesar el resultado
workflow.add_edge("tools", "agent")

# 5. Compilación del Grafo
graph = workflow.compile()
