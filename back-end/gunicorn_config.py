import multiprocessing
import os

# Configuración de Gunicorn
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
timeout = 120
accesslog = '-'
errorlog = '-'

# Nombre de la aplicación
proc_name = 'shopify_agent_back_end'
