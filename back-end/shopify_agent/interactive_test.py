import os
import sys
import django

# 1. Asegurar que el directorio actual esté en la ruta para que reconozca los paquetes
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
            
            # Ejecutar el grafo
            final_state = graph.invoke({"messages": messages})
            
            # Obtener el último mensaje
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
