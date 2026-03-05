import os
import logging
from langchain_core.tools import tool
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@tool
def send_stock_alert(product_id: str, product_name: str, stock_level: int):
    """Envía una alerta de stock bajo y persiste en Supabase."""
    
    # Alerta por consola (por ahora)
    msg = f"ALERTA: Stock crítico para {product_name} (ID: {product_id}). Stock actual: {stock_level}"
    print(msg)
    
    try:
        supabase = get_supabase_client()
        data = {
            "product_id": product_id,
            "product_name": product_name,
            "stock_level": stock_level,
            "status": "notified"
        }
        # Inserción en la tabla de notificaciones de bajo stock
        response = supabase.table("low_stock_alerts").insert(data).execute()
        return f"Alerta guardada exitosamente en Supabase (ID de registro: {response.data[0]['id']})"
    except Exception as e:
        return f"Error al guardar en Supabase: {str(e)}"
