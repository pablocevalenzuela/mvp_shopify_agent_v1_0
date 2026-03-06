import os
from pathlib import Path
import environ

# BASE_DIR apunta ahora dos niveles arriba por estar en settings/
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Initialize django-environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)


SECRET_KEY = os.getenv(
    'SECRET_KEY', 'django-insecure-yf@cdwxmm#c9hmuohd3j#w46+nx1g@pwob7d7=8*cgjy9jkmtc')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'shopify_agent',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
"""

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'UTC'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'


# Shopify API Credentials
SHOPIFY_API_KEY = env('SHOPIFY_API_KEY', default=None)
SHOPIFY_API_PASSWORD = env('SHOPIFY_API_PASSWORD', default=None)
SHOPIFY_WEBHOOK_SECRET = env('SHOPIFY_WEBHOOK_SECRET', default=None)
SHOPIFY_STORE_NAME = env('SHOPIFY_STORE_NAME', default=None)
