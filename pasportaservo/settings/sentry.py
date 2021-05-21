import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import get_env_setting


def sentry_init(env=None):
    sentry_sdk.init(
        dsn=get_env_setting("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        environment={"PROD": "production", "UAT": "staging"}.get(env, "development"),
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        # send_default_pii=True,
    )
