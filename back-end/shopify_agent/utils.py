import os
import requests
import json
from django.conf import settings

def get_shopify_product_details(inventory_item_id: str):
    """
    Consulta la API GraphQL de Shopify para obtener el título y SKU 
    a partir de un inventory_item_id.
    """
    # Usamos SHOPIFY_STORE_NAME tal como el usuario lo tiene configurado
    store_name = os.getenv('SHOPIFY_STORE_NAME')
    access_token = os.getenv('SHOPIFY_ADMIN_ACCESS_TOKEN')
    api_version = "2024-01" 
    
    if not store_name or not access_token:
        print("[SHOPIFY API] Error: Faltan credenciales (SHOPIFY_STORE_NAME o ACCESS_TOKEN) en .env")
        return None

    # Construimos la URL completa de la tienda
    shop_domain = f"{store_name}.myshopify.com"
    url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
    
    # Query para obtener SKU y Título del Producto
    query = """
    query($id: ID!) {
      inventoryItem(id: $id) {
        sku
        variant {
          title
          product {
            title
          }
        }
      }
    }
    """
    
    # Formatear el ID para GraphQL si viene solo como número
    if not str(inventory_item_id).startswith("gid://"):
        gid = f"gid://shopify/InventoryItem/{inventory_item_id}"
    else:
        gid = inventory_item_id

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    
    try:
        response = requests.post(url, json={'query': query, 'variables': {'id': gid}}, headers=headers)
        data = response.json()
        
        if "errors" in data:
            print(f"[SHOPIFY API] Errores GraphQL: {data['errors']}")
            return None
            
        item = data.get("data", {}).get("inventoryItem")
        if not item:
            return None
            
        product_title = item.get("variant", {}).get("product", {}).get("title")
        variant_title = item.get("variant", {}).get("title")
        full_title = f"{product_title} ({variant_title})" if variant_title != "Default Title" else product_title
        
        return {
            "title": full_title,
            "sku": item.get("sku")
        }
    except Exception as e:
        print(f"[SHOPIFY API] Error de conexión: {e}")
        return None
