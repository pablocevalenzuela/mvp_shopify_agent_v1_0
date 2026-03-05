from .base import *
import environ
import os

# Cargar variables de entorno específicas de desarrollo
# El método read_env carga el archivo al os.environ
environ.Env.read_env(os.path.join(BASE_DIR, '.env.develop'))

# Sobrescribimos el DEBUG si es necesario
DEBUG = True

DATABASES = {
    # Lee la variable DATABASE_URL de .env.develop y la configura para Django.
    # Nota: env viene importado desde .base
    'default': env.db('DATABASE_URL')
}

# Otras configuraciones de desarrollo (ej: emails a consola)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
