
from pathlib import Path

from Utils import Config as QSRConfig


BASE_DIR = Path(__file__).resolve().parent.parent


import os

SECRET_KEY = os.getenv('QSR_SECRET_KEY', 'django-insecure-uu67n3p4qebcb9qyq^i!2b%*w(x88!8myket&uqh1!xe_6q@((')


DEBUG = os.getenv('QSR_DEBUG', '1') == '1'

ALLOWED_HOSTS = [h for h in os.getenv('QSR_ALLOWED_HOSTS', '').split(',') if h]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'forecast',
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

ROOT_URLCONF = 'ML_QSR.urls'

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
                'forecast.context_processors.qsr',
            ],
        },
    },
]

WSGI_APPLICATION = 'ML_QSR.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': QSRConfig.DB_DATABASE,
        'USER': QSRConfig.DB_USERNAME,
        'PASSWORD': QSRConfig.DB_PASSWORD,
        'HOST': QSRConfig.DB_SERVER,
        'PORT': QSRConfig.DB_PORT,
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'vi'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGIN_URL = 'forecast:login'
