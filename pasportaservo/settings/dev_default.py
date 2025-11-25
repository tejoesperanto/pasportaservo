import os

# Import dev as the default, but only when no explicit settings were chosen.
# If DJANGO_SETTINGS_MODULE points to a sub-module (e.g.,
# `pasportaservo.settings.testing_local`), avoid importing so the sub-module
# can load cleanly.
_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
if not _settings_module or _settings_module == 'pasportaservo.settings':
    from .dev import *  # noqa: F401, F403
del _settings_module
