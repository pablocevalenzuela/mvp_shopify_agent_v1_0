from typing import Annotated, TypedDict, List, Union
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Usamos add_messages para manejar el historial de forma eficiente
    messages: Annotated[List[BaseMessage], add_messages]
    # Datos del producto recibidos del webhook
    product_data: dict
    # Bandera para saber si ya se notificó
    notified: bool
