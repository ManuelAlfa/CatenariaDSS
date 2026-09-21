from __future__ import annotations

from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Loads entorno.env (ignored by git via *.env) to keep parity with current project.
# apps/core/couchbase_client.py already loads it too, but we load early so other settings can use it.
load_dotenv(dotenv_path=BASE_DIR / "entorno.env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "catenarias.solutia.sbs,0.0.0.0,127.0.0.1,localhost,testserver").split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = ['https://catenaria.catenaria-lab.com']

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps del proyecto (estructura profesional)
    "apps.core",
    "apps.usuarios",
    "apps.analitica",
    "apps.alertas",
    "apps.tramos",
    "apps.umbrales",
    "apps.operaciones",
    "apps.consultas",
    "apps.sync",
    "apps.dss",
    "apps.kpi_kgi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.core.middleware.GlobalHtmlErrorMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "apps.core.middleware.LegacyCsrfFormInjectionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.CouchbaseAuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "catenarias.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "catenarias.wsgi.application"
ASGI_APPLICATION = "catenarias.asgi.application"

# Couchbase-only mode: disable relational default DB.
# Couchbase-only mode: disable relational default DB.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.dummy",
    }
}

AUTH_PASSWORD_VALIDATORS = []

AUTHENTICATION_BACKENDS = [
    "apps.core.auth_backend.CouchbaseUsersBackend",
]

LOGIN_URL = "/"
CSRF_FAILURE_VIEW = "apps.core.views.csrf_failure"
# Avoid relational-session dependency (django_session table) in Couchbase-oriented setup.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "img"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

