"""
Django settings for schindia_backend project.
Uses SQLite for all environments (local dev and AWS ECS via EFS mount).
DynamoDB is used alongside Django via boto3 for billing/invoices data.

DJANGO_ENV controls behaviour:
  development  — local machine, SQLite, no AWS services required
  dev          — AWS ECS dev stack, ShichidaInvoices-dev, shichida-dev S3 bucket
  production   — AWS ECS prod stack, ShichidaInvoices-prod, shichida-prod S3 bucket
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Environment ──────────────────────────────────────────────────────────────
# Possible values: development | dev | production
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')

IS_LOCAL       = DJANGO_ENV == 'development'
IS_DEV         = DJANGO_ENV == 'dev'
IS_PRODUCTION  = DJANGO_ENV == 'production'
IS_AWS         = IS_DEV or IS_PRODUCTION   # any deployed environment

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-+c_lvjehmrq#bxg0@$tizbte#_mc2h!1rrzgibeg-lxlnx75d2'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

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

# Database — always SQLite; path overridden via DJANGO_DB_PATH in production (EFS mount)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
    }
}

# Custom User Model
AUTH_USER_MODEL = 'schindia_auth.User'

# Password hashing — prefer argon2 as per security requirements
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
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

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://localhost:3000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ────────────────────────────────────────────────────────────────────────
# AWS — region (shared)
# ────────────────────────────────────────────────────────────────────────

AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')

# ────────────────────────────────────────────────────────────────────────
# DynamoDB — table names are environment-specific so dev and prod data
# never share a table.
#
#   dev   →  ShichidaInvoices-dev,  ShichidaCenters-dev,  ...
#   prod  →  ShichidaInvoices-prod, ShichidaCenters-prod, ...
#   local →  env var or DynamoDB Local via DYNAMODB_ENDPOINT
# ────────────────────────────────────────────────────────────────────────

DYNAMODB_REGION   = os.environ.get('DYNAMODB_REGION', AWS_REGION)
# Set to http://localhost:8001 to use DynamoDB Local in development
DYNAMODB_ENDPOINT = os.environ.get('DYNAMODB_ENDPOINT', None)

# Table names — injected by ECS task definition for AWS envs,
# fall back to sensible local defaults.
_DDB_SUFFIX = f'-{DJANGO_ENV}' if IS_AWS else '-local'

DYNAMODB_INVOICES_TABLE  = os.environ.get('DYNAMODB_INVOICES_TABLE',  f'ShichidaInvoices{_DDB_SUFFIX}')
DYNAMODB_CENTERS_TABLE   = os.environ.get('DYNAMODB_CENTERS_TABLE',   f'ShichidaCenters{_DDB_SUFFIX}')
DYNAMODB_CHILDREN_TABLE  = os.environ.get('DYNAMODB_CHILDREN_TABLE',  f'ShichidaChildren{_DDB_SUFFIX}')
DYNAMODB_USERS_TABLE     = os.environ.get('DYNAMODB_USERS_TABLE',     f'ShichidaUsers{_DDB_SUFFIX}')
DYNAMODB_ROLES_TABLE     = os.environ.get('DYNAMODB_ROLES_TABLE',     f'ShichidaRoles{_DDB_SUFFIX}')

# ────────────────────────────────────────────────────────────────────────
# S3 — separate bucket per environment so dev uploads never land in prod.
#
#   dev   →  shichida-uploads-dev
#   prod  →  shichida-uploads-prod
#   local →  not used (no S3 storage locally)
# ────────────────────────────────────────────────────────────────────────

_S3_DEFAULT_BUCKET = f'shichida-uploads-{DJANGO_ENV}' if IS_AWS else ''

AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_S3_BUCKET', _S3_DEFAULT_BUCKET)
AWS_S3_REGION_NAME      = AWS_REGION
AWS_DEFAULT_ACL         = None
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

if IS_AWS and AWS_STORAGE_BUCKET_NAME:
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    # Static files served from environment-specific S3 bucket
    STATICFILES_STORAGE  = 'storages.backends.s3boto3.S3StaticStorage'
    STATIC_URL           = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# ────────────────────────────────────────────────────────────────────────
# SES — emails sent from an environment-specific sender address so dev
# test emails are clearly distinguishable from production emails.
#
#   dev   →  dev@shichida.in
#   prod  →  noreply@shichida.in
# ────────────────────────────────────────────────────────────────────────

_SES_SENDER_DEFAULT = 'dev@shichida.in' if IS_DEV else 'noreply@shichida.in'
AWS_SES_SENDER = os.environ.get('AWS_SES_SENDER', _SES_SENDER_DEFAULT)

if IS_AWS:
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = f'email-smtp.{AWS_REGION}.amazonaws.com'
    EMAIL_PORT          = 587
    EMAIL_USE_TLS       = True
    EMAIL_HOST_USER     = os.environ.get('AWS_SES_SMTP_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('AWS_SES_SMTP_PASSWORD', '')
    DEFAULT_FROM_EMAIL  = AWS_SES_SENDER

# ────────────────────────────────────────────────────────────────────────
# Production-only security hardening
# (dev stack on AWS stays permissive for easier debugging)
# ────────────────────────────────────────────────────────────────────────

if IS_PRODUCTION:
    DEBUG = False
    AWS_STORAGE_BUCKET_NAME  = os.environ.get('AWS_S3_BUCKET', 'shichida-uploads-production')
    AWS_S3_CUSTOM_DOMAIN     = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    STATIC_URL               = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    DYNAMODB_INVOICES_TABLE  = os.environ.get('DYNAMODB_INVOICES_TABLE',  'ShichidaInvoices-production')
    DYNAMODB_CENTERS_TABLE   = os.environ.get('DYNAMODB_CENTERS_TABLE',   'ShichidaCenters-production')
    DYNAMODB_CHILDREN_TABLE  = os.environ.get('DYNAMODB_CHILDREN_TABLE',  'ShichidaChildren-production')
    DYNAMODB_USERS_TABLE     = os.environ.get('DYNAMODB_USERS_TABLE',     'ShichidaUsers-production')
    DYNAMODB_ROLES_TABLE     = os.environ.get('DYNAMODB_ROLES_TABLE',     'ShichidaRoles-production')
    SECURE_SSL_REDIRECT            = True
    SECURE_REDIRECT_EXEMPT          = [r'^api/auth/login/']
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    SECURE_PROXY_SSL_HEADER        = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Remove browsable API renderer in production
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
    )

# ────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if IS_AWS else 'DEBUG',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
