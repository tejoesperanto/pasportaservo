from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.db import models

from djangocodemirror.widgets import CodeMirrorAdminWidget
from solo.admin import SingletonModelAdmin

from .models import Policy, SiteConfiguration

admin.site.register(SiteConfiguration, SingletonModelAdmin)
admin.site.unregister(FlatPage)


@admin.register(FlatPage)
class FlatPageAdmin(FlatPageAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CodeMirrorAdminWidget(config_name='html')},
    }


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = (
        'version', 'effective_date', 'requires_consent',
    )
    ordering = ('-effective_date', )
    formfield_overrides = {
        models.TextField: {'widget': CodeMirrorAdminWidget(config_name='html')},
    }

    def has_delete_permission(self, request, obj=None):
        return False
