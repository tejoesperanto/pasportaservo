from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.db import models
from djangocodemirror.widgets import CodeMirrorAdminWidget
from solo.admin import SingletonModelAdmin

from .models import SiteConfiguration

admin.site.register(SiteConfiguration, SingletonModelAdmin)
admin.site.unregister(FlatPage)


@admin.register(FlatPage)
class FlatPageAdmin(FlatPageAdmin):
    formfield_overrides = {
        models.TextField: {"widget": CodeMirrorAdminWidget(config_name="html")},
    }
