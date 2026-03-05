from .base import *
from dotenv import load_dotenv
import os

# Cargar variables de entorno específicas de desarrollo
dotenv_path = os.path.join(BASE_DIR, '.env.develop')
load_dotenv(dotenv_path)

DEBUG = True

# Otras configuraciones de desarrollo (ej: emails a consola)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
