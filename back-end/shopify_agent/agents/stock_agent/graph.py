import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_openai import ChatOpenAI
from shopify_agent.agents.stock_agent.state import AgentState
from shopify_agent.agents.stock_agent.tools import send_stock_alert
from shopify_agent.agents.stock_agent.prompts import SYSTEM_PROMPT

# Definir herramientas
tools = [send_stock_alert]
tool_node = ToolNode(tools)

# Modelo LLM
# Se recomienda usar modelos como 'gpt-4o-mini' para optimizar costos sin sacrificar razonamiento
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# El grafo ReAct simplificado utilizando el asistente predefinido de LangGraph
# Esto asegura que el patrón ReAct se implemente con la mínima latencia y overhead de tokens
graph = create_react_agent(llm, tools, state_modifier=SYSTEM_PROMPT)
