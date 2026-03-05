import os
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from shopify_agent.agents.stock_agent.tools import send_stock_alert
from shopify_agent.agents.stock_agent.prompts import SYSTEM_PROMPT

# Definir herramientas
tools = [send_stock_alert]

# Configuración del LLM usando GitHub Models (vía Azure Inference)
# Obtenemos el token desde las variables de entorno cargadas por Django/dotenv
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("GITHUB_TOKEN"),
    base_url="https://models.inference.ai.azure.com",
    temperature=0,
    max_tokens=1000
)

# El grafo ReAct de LangGraph
# Cambiamos state_modifier por prompt para asegurar compatibilidad
graph = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
