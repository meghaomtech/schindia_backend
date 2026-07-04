"""
Django settings for schindia_backend project.
Supports two environments:
  - local: SQLite database, debug mode
  - production: AWS RDS PostgreSQL, S3 storage, SES email
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# CORE SETTINGS
# =============================================================================

DJANGO_ENV = config('DJANGO_ENV', default='local')  # 'local' or 'production'
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-dev-key-change-me')
DEBUG = config('DJANGO_DEBUG', default='True', cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'storages',
    # Local apps
    'schindia_auth',
    'centres',
    'sessions_app',
    'children',
    'progress',
    'billing',
    'roles',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'schindia_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'schindia_backend.wsgi.application'

# =============================================================================
# DATABASE - Local (SQLite) vs Production (AWS RDS PostgreSQL)
# =============================================================================

if DJANGO_ENV == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('PROD_DB_NAME', default='shichida'),
            'USER': config('PROD_DB_USER', default='shichida_admin'),
            'PASSWORD': config('PROD_DB_PASSWORD', default=''),
            'HOST': config('PROD_DB_HOST', default=''),
            'PORT': config('PROD_DB_PORT', default='5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =============================================================================
# CUSTOM USER MODEL
# =============================================================================

AUTH_USER_MODEL = 'schindia_auth.User'

# Password hashing — prefer argon2 as per security requirements
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# AWS CONFIGURATION
# =============================================================================

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_REGION = config('AWS_REGION', default='ap-south-1')
AWS_S3_REGION_NAME = AWS_REGION

# S3 Storage (for file uploads - production only)
if DJANGO_ENV == 'production' and AWS_ACCESS_KEY_ID:
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_S3_BUCKET', 'shichida-uploads-production')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False

    # Use S3 for media/static files in production
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

    # DynamoDB table names
    DYNAMODB_INVOICES_TABLE = os.environ.get('DYNAMODB_INVOICES_TABLE', 'ShichidaInvoices-production')
    DYNAMODB_CENTRES_TABLE = os.environ.get('DYNAMODB_CENTRES_TABLE', 'ShichidaCentres-production')
    DYNAMODB_CHILDREN_TABLE = os.environ.get('DYNAMODB_CHILDREN_TABLE', 'ShichidaChildren-production')
    DYNAMODB_SESSIONS_TABLE = os.environ.get('DYNAMODB_SESSIONS_TABLE', 'ShichidaSessions-production')
    DYNAMODB_SLOTS_TABLE = os.environ.get('DYNAMODB_SLOTS_TABLE', 'ShichidaSlots-production')
    DYNAMODB_CONTACTS_TABLE = os.environ.get('DYNAMODB_CONTACTS_TABLE', 'ShichidaContacts-production')
    DYNAMODB_PURCHASES_TABLE = os.environ.get('DYNAMODB_PURCHASES_TABLE', 'ShichidaPurchases-production')

# =============================================================================
# EMAIL CONFIGURATION (AWS SES for production)
# =============================================================================

if DJANGO_ENV == 'production' and AWS_ACCESS_KEY_ID:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = f'email-smtp.{AWS_REGION}.amazonaws.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    # SES SMTP credentials are NOT IAM access keys — generate them separately
    # via AWS Console → SES → SMTP Settings → Create SMTP credentials
    EMAIL_HOST_USER = config('SES_SMTP_USER', default='')
    EMAIL_HOST_PASSWORD = config('SES_SMTP_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('AWS_SES_SENDER', default='noreply@shichida.in')
else:
    # Local: print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# =============================================================================
# JWT SETTINGS
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://localhost:3000',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# SECURITY (Production only)
# =============================================================================

if DJANGO_ENV == 'production':
    # DynamoDB table names for production
    DYNAMODB_USERS_TABLE = os.environ.get('DYNAMODB_USERS_TABLE', 'ShichidaUsers-production')
    DYNAMODB_ROLES_TABLE = os.environ.get('DYNAMODB_ROLES_TABLE', 'ShichidaRoles-production')

    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r'^api/auth/login/']
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
}
