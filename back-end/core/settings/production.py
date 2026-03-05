from .base import *
from dotenv import load_dotenv
import os

# Cargar variables de entorno específicas de producción
dotenv_path = os.path.join(BASE_DIR, '.env.production')
load_dotenv(dotenv_path)

DEBUG = False

# Seguridad en producción
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = True # Solo si tienes SSL configurado
