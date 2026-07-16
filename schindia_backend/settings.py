"""
Django settings for schindia_backend project.
Supports two environments:
  - local: SQLite database, debug mode
  - production: AWS RDS PostgreSQL, S3 storage, SES email
"""

import os
import sys
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

sys.setrecursionlimit(5000)

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
    'django.contrib.staticfiles',
    # contenttypes + auth are required transitively by rest_framework_simplejwt's
    # own models.py (TokenUser references auth.Group/auth.Permission at import
    # time) — they're never queried since we don't use Django's ORM User, and
    # DATABASES is a dummy backend, so no SQLite table for them ever gets created.
    'django.contrib.contenttypes',
    'django.contrib.auth',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
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
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'schindia_backend.wsgi.application'

# =============================================================================
# DATABASE - DynamoDB is the only datastore. The dummy backend means any
# accidental ORM call fails immediately instead of silently touching SQLite.
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',
    }
}

# =============================================================================
# PASSWORD HASHING
# =============================================================================

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

if DJANGO_ENV in ('production', 'dev') and AWS_ACCESS_KEY_ID:
    # Use SES via boto3 (uses IAM credentials directly, no SMTP creds needed)
    EMAIL_BACKEND = 'django_ses.SESBackend'
    AWS_SES_REGION_NAME = AWS_REGION
    AWS_SES_REGION_ENDPOINT = f'email.{AWS_REGION}.amazonaws.com'
    DEFAULT_FROM_EMAIL = config('AWS_SES_SENDER', default='noreply@shichida.in')
else:
    # Local: print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'schindia_auth.authentication.DynamoAwareJWTAuthentication',
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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),   # Short-lived; session length is the refresh token's job
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),      # Req 26.5: 7 days for remember me / Req 26.1: 24h session via refresh
    # No rest_framework_simplejwt.token_blacklist app (that's an ORM/SQLite-backed
    # table) — revocation instead happens via the DynamoDB blacklist on logout
    # (schindia_auth.authentication.DynamoAwareJWTAuthentication), so refresh
    # tokens are not rotated/blacklisted on refresh.
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
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

# Frontend URL for email links (login, onboarding, etc.)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

# =============================================================================
# SECURITY (Production only)
# =============================================================================

if DJANGO_ENV == 'production':
    # DynamoDB table names for production
    DYNAMODB_USERS_TABLE = os.environ.get('DYNAMODB_USERS_TABLE', 'ShichidaUsers-production')
    DYNAMODB_ROLES_TABLE = os.environ.get('DYNAMODB_ROLES_TABLE', 'ShichidaRoles-production')

    # SSL settings - only enable when HTTPS is configured (set ENABLE_SSL=True in .env)
    if config('ENABLE_SSL', default='False', cast=bool):
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
