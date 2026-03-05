import time

# En un sistema real, usar Redis o la misma DB de Supabase con TTL
# Por ahora usaremos un cache en memoria para la demostración
_DEDUPE_CACHE = {}

def should_process(product_id: str, stock_level: int) -> bool:
    """
    Decide si procesar una alerta de stock.
    Optimización: No procesar si ya notificamos este nivel de stock en la última hora.
    """
    key = f"{product_id}_{stock_level}"
    current_time = time.time()
    
    if key in _DEDUPE_CACHE:
        last_time = _DEDUPE_CACHE[key]
        if current_time - last_time < 3600:  # 1 hora
            return False
            
    _DEDUPE_CACHE[key] = current_time
    return True
