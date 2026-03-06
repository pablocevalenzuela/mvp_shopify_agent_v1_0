import os
import sys
import django

# 1. Asegurar que el directorio actual esté en la ruta
sys.path.append(os.getcwd())

# 2. Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.develop')
django.setup()

# 3. Importar después de configurar django
from shopify_agent.agents.stock_agent.graph import graph

def chat_with_agent():
    print("\n--- 🤖 Chat Interactivo con el Agente LangGraph ---")
    print("Escribe 'salir' para terminar.\n")
    
    messages = []
    
    while True:
        try:
            user_input = input("Tú: ")
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("¡Adiós!")
                break
                
            messages.append(("user", user_input))
            
            # Ejecutar el grafo paso a paso (stream) para ver las llamadas a herramientas
            print("--- Pensando ---")
            for chunk in graph.stream({"messages": messages}, stream_mode="values"):
                # Si hay mensajes de herramienta, los mostramos para debug
                if "messages" in chunk:
                    last_msg = chunk["messages"][-1]
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        print(f"🔧 Ejecutando herramienta: {last_msg.tool_calls[0]['name']}")
                    # Si es un mensaje de tipo ToolMessage (resultado)
                    if last_msg.type == "tool":
                        print(f"📦 Resultado de herramienta: {last_msg.content}")
            
            # El estado final tras todo el flujo
            final_state = graph.invoke({"messages": messages})
            ai_response = final_state["messages"][-1]
            
            print(f"Agente: {ai_response.content}")
            
            # Actualizamos nuestro historial
            messages = final_state["messages"]
            
        except KeyboardInterrupt:
            print("\n¡Adiós!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    chat_with_agent()
