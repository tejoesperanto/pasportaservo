from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HostingConfig(AppConfig):
    name = "hosting"
    verbose_name = _("Hosting Service")
