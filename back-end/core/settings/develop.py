from .base import *
# from dotenv import load_dotenv
import environ
import os

# Cargar variables de entorno específicas de desarrollo
# dotenv_path = os.path.join(BASE_DIR, '.env.develop')
# load_dotenv(dotenv_path)

environ.Env.read_env(os.path.join(BASE_DIR, '.env.develop'))

DEBUG = True

DATABASES = {
    # Lee la variable DATABASE_URL de .env.develop y la configura para Django.
    'default': env.db('DATABASE_URL')
}

# Otras configuraciones de desarrollo (ej: emails a consola)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
