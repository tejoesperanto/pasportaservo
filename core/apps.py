from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = _("Hosting Service Core")
