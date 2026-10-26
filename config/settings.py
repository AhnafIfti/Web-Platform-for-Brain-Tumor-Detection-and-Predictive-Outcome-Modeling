"""Environment-based configuration; private MRI files are never public media."""
import os
from pathlib import Path
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Set SECRET_KEY, or set DEBUG=true for local development.')
    SECRET_KEY = 'development-only-neurovision-do-not-use-in-production'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
CSRF_TRUSTED_ORIGINS = list(filter(None, os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')))
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django_otp', 'django_otp.plugins.otp_totp',
    'dashboard', 'analysis', 'performance', 'accounts',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware', 'accounts.middleware.RequireSecondFactor',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages', 'dashboard.context.brand',
              ]}}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
DATABASES = {'default': dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60)}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(BASE_DIR / 'media')))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
REGISTRATION_ENABLED = os.getenv('REGISTRATION_ENABLED', 'false').lower() == 'true'
MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '128'))
MAX_VOLUME_VOXELS = int(os.getenv('MAX_VOLUME_VOXELS', '16777216'))
MAX_VOLUME_SLICES = int(os.getenv('MAX_VOLUME_SLICES', '512'))
MAX_UNCOMPRESSED_MRI_MB = int(os.getenv('MAX_UNCOMPRESSED_MRI_MB', '256'))
ALLOWED_MRI_EXTENSIONS = ('.nii', '.nii.gz')
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 2
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_HANDLERS = ['analysis.upload_handlers.LimitedUploadHandler',
                        'django.core.files.uploadhandler.TemporaryFileUploadHandler']
MODEL_CHECKPOINT_PATH = Path(os.getenv('MODEL_CHECKPOINT_PATH') or BASE_DIR / 'ml_models/checkpoints/swin_tiny_unet.pth')
MODEL_VERSION = os.getenv('MODEL_VERSION', 'swin-tiny-unet-v2')
MODEL_DEVICE = os.getenv('MODEL_DEVICE', 'auto')
SEGMENTATION_THRESHOLD = float(os.getenv('SEGMENTATION_THRESHOLD', '0.5'))
if not 0 < SEGMENTATION_THRESHOLD < 1:
    raise ImproperlyConfigured('SEGMENTATION_THRESHOLD must be strictly between 0 and 1.')
BENCHMARK_CSV = Path(os.getenv('BENCHMARK_CSV') or BASE_DIR / 'data/benchmarks/notebook_results.csv')
MAX_ACTIVE_ANALYSES_PER_USER = 2
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
X_FRAME_OPTIONS = 'DENY'
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'root': {'handlers': ['console'], 'level': 'INFO'}}

OTP_TOTP_ISSUER = 'NeuroVision AI'
