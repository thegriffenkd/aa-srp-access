from allianceauth.project_template.project_name.settings.base import *  # noqa: F403

INSTALLED_APPS += ["allianceauth.srp", "srp_access"]  # noqa: F405
ROOT_URLCONF = "testauth.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/15",
        "OPTIONS": {"SOCKET_CONNECT_TIMEOUT": 1, "SOCKET_TIMEOUT": 1},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
LOGGING = {"version": 1, "disable_existing_loggers": True}
SITE_URL = "https://test.invalid"
ALLOWED_HOSTS = ["testserver", "test.invalid"]
CSRF_TRUSTED_ORIGINS = [SITE_URL]
ESI_SSO_CALLBACK_URL = f"{SITE_URL}/sso/callback"
ESI_SSO_CLIENT_ID = "test-client-id"
ESI_SSO_CLIENT_SECRET = "test-client-secret"
ESI_USER_CONTACT_EMAIL = "test@example.invalid"
DEFAULT_FROM_EMAIL = "test@example.invalid"
