import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import CURRENT_COMMIT, get_env_setting


def sentry_init(env=None):
    sentry_sdk.init(
        dsn=get_env_setting('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        environment={'PROD': "production", 'UAT': "staging"}.get(env, "development"),
        release=CURRENT_COMMIT[0] or None,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        # send_default_pii=True,

        # Percentage of error events to sample.
        sample_rate=1.0,
        # Percentage of transaction events to sample for performance monitoring.
        traces_sample_rate=0.75,
    )
