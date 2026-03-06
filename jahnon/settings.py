import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-jahnon-on-wheels-2026'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# CORS - allow all for local dev
CORS_ALLOW_ALL_ORIGINS = True

# Avoid redirect overhead on trailing slashes
APPEND_SLASH = True

ROOT_URLCONF = 'jahnon.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.MessageMiddleware' if False else 'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'jahnon.wsgi.application'

# Database — same PostgreSQL on Render
DATABASE_URL = os.getenv('DATABASE_URL', '')
# Parse the asyncpg URL into Django format
_db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

if _db_url:
    import re
    m = re.match(r'postgresql://([^:]+):([^@]+)@([^/]+)/(.+)', _db_url)
    if m:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': m.group(4),
                'USER': m.group(1),
                'PASSWORD': m.group(2),
                'HOST': m.group(3).split(':')[0] if ':' in m.group(3) else m.group(3),
                'PORT': m.group(3).split(':')[1] if ':' in m.group(3) else '5432',
                'CONN_MAX_AGE': 600,           # Keep DB connections alive for 10 min (avoid reconnect overhead)
                'CONN_HEALTH_CHECKS': True,    # Verify connection is alive before using it
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

LANGUAGE_CODE = 'he'
TIME_ZONE = 'Asia/Jerusalem'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
