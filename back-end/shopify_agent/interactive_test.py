import os
import django
import json

# 1. Configurar el entorno de Django para poder importar los módulos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.develop')
django.setup()

# 2. Importar el agente compilado
from shopify_agent.agents.stock_agent.graph import graph

def chat_with_agent():
    print("\n--- 🤖 Chat Interactivo con el Agente LangGraph ---")
    print("Escribe 'salir' para terminar.\n")
    
    # El estado inicial del historial de mensajes
    messages = []
    
    while True:
        user_input = input("Tú: ")
        
        if user_input.lower() in ['salir', 'exit', 'quit']:
            print("¡Adiós!")
            break
            
        # Añadir el mensaje del usuario al historial
        messages.append(("user", user_input))
        
        # Ejecutar el grafo de LangGraph
        try:
            # Invocamos el grafo con el historial de mensajes acumulado
            # Nota: Usamos invoke() para obtener el resultado final tras pasar por los nodos
            final_state = graph.invoke({"messages": messages})
            
            # Obtener el último mensaje (la respuesta de la IA)
            ai_response = final_state["messages"][-1]
            
            print(f"Agente: {ai_response.content}")
            
            # Actualizamos nuestro historial local con la respuesta de la IA
            # para mantener el contexto en la siguiente pregunta.
            messages = final_state["messages"]
            
        except Exception as e:
            print(f"❌ Error al llamar al agente: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    chat_with_agent()
