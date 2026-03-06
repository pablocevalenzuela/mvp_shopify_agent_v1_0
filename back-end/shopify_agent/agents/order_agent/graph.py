import os
from typing import Literal
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from shopify_agent.agents.stock_agent.state import AgentState # Reutilizamos el estado base
from shopify_agent.agents.order_agent.tools import get_pending_stock_alert, place_provider_order
from shopify_agent.agents.order_agent.prompts import SYSTEM_PROMPT

# 1. Definir herramientas
tools = [get_pending_stock_alert, place_provider_order]
tool_node = ToolNode(tools)

# 2. Configurar el LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("GITHUB_TOKEN"),
    base_url="https://models.inference.ai.azure.com",
    temperature=0,
).bind_tools(tools)

# 3. Nodos
def call_model(state: AgentState, config):
    thread_id = config.get("configurable", {}).get("thread_id")
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    response = llm.invoke(messages, config)
    
    # Inyectar thread_id automáticamente en get_pending_stock_alert si se invoca
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "get_pending_stock_alert":
                tool_call["args"]["thread_id"] = thread_id

    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 4. Grafo con Memoria
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
