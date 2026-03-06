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
            
            # Ejecutar el grafo paso a paso (stream) y capturar el estado final
            print("--- Pensando ---")
            final_chunk = None
            for chunk in graph.stream({"messages": messages}, stream_mode="values"):
                final_chunk = chunk # Vamos guardando el último chunk
                
                if "messages" in chunk:
                    last_msg = chunk["messages"][-1]
                    # Mostrar cuando la IA decide usar una herramienta
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        print(f"🔧 Ejecutando herramienta: {last_msg.tool_calls[0]['name']}")
                    # Mostrar el resultado de la herramienta
                    if hasattr(last_msg, "type") and last_msg.type == "tool":
                        print(f"📦 Resultado de herramienta: {last_msg.content}")
            
            # Extraemos la respuesta final del último chunk del stream
            if final_chunk and "messages" in final_chunk:
                ai_response = final_chunk["messages"][-1]
                print(f"Agente: {ai_response.content}")
                # Actualizamos el historial para la siguiente vuelta
                messages = final_chunk["messages"]
            
        except KeyboardInterrupt:
            print("\n¡Adiós!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    chat_with_agent()
