from typing import cast

from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.core.cache import cache
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from djangocodemirror.widgets import CodeMirrorAdminWidget
from packvers import version
from solo.admin import SingletonModelAdmin

from hosting.models import Profile

from ..models import Agreement, Policy, SiteConfiguration, UserBrowser
from .filters import DependentFieldFilter, YearBracketFilter

admin.site.index_template = 'admin/custom_index.html'
admin.site.disable_action('delete_selected')

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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if 'version' in form.changed_data or 'effective_date' in form.changed_data:
            # Bust the cache of references to all policies;
            # these references are cached indefinitely otherwise.
            cache.delete('all-policies')


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'policy_link', 'user_link', 'created', 'modified', 'withdrawn',
    )
    ordering = ('-policy_version', '-modified', 'user__username')
    search_fields = ('user__username',)
    list_filter = ('policy_version',)
    date_hierarchy = 'created'
    fields = (
        'user_link', 'policy_link',
        'created', 'modified', 'withdrawn',
    )
    readonly_fields = [f.name for f in Agreement._meta.fields] + ['user_link', 'policy_link']

    @admin.display(
        description=_("user"),
        ordering='user__username',
    )
    def user_link(self, obj: Agreement):
        try:
            link = reverse('admin:auth_user_change', args=[obj.user.pk])
            account_link = f'<a href="{link}">{obj.user}</a>'
            try:
                profile_link = '&nbsp;(<a href="{url}">{name}</a>)</sup>'.format(
                    url=obj.user.profile.get_admin_url(), name=_("profile"))
            except Profile.DoesNotExist:
                profile_link = ''
            return format_html(" ".join([account_link, profile_link]))
        except AttributeError:
            return format_html('{userid} <sup>?</sup>', userid=obj.user_id)

    @admin.display(
        description=_("version of policy"),
        ordering='policy_version',
    )
    def policy_link(self, obj: Agreement):
        try:
            cache = self._policies_cache
        except AttributeError:
            cache = self._policies_cache = {}
        if obj.policy_version in cache:
            return cache[obj.policy_version]
        value = obj.policy_version
        try:
            policy = Policy.objects.get(version=obj.policy_version)
            link = reverse('admin:core_policy_change', args=[policy.pk])
            value = format_html(
                '<a href="{url}">{policy}</a>',
                url=link, policy=obj.policy_version)
        except Policy.DoesNotExist:
            pass
        finally:
            cache[obj.policy_version] = value
        return value

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'user__profile')
        qs = qs.only(
                *[f.name for f in Agreement._meta.fields],
                'user__id', 'user__username', 'user__profile__id')
        return qs

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserBrowser)
class UserBrowserAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'os_name', 'os_version', 'browser_name', 'browser_version', 'added_on',
    )
    ordering = ('user__username', '-added_on')
    search_fields = ('user__username__exact',)
    list_filter = (
        'os_name',
        DependentFieldFilter.configure(
            'os_name', 'os_version',
            coerce=lambda version_string: version.parse(version_string),
            sort=True, sort_reverse=True,
        ),
        'browser_name',
        DependentFieldFilter.configure(
            'browser_name', 'browser_version',
            coerce=lambda version_string: version.parse(version_string),
            sort=True, sort_reverse=True,
        ),
        ('added_on', YearBracketFilter.configure(YearBracketFilter.Brackets.SINCE)),
    )
    show_full_result_count = False
    fields = (
        'user_agent_string', 'user_agent_hash',
        'os_name', 'os_version', 'browser_name', 'browser_version', 'device_type',
        'geolocation',
    )
    raw_id_fields = ('user',)
    readonly_fields = ('added_on',)

    @admin.display(
        description=_("user"),
        ordering='user__username',
    )
    def user_link(self, obj: UserBrowser):
        try:
            link = reverse('admin:auth_user_change', args=[obj.user.pk])
            return format_html('<a href="{link}">{user}</a>', link=link, user=obj.user)
        except AttributeError:
            return format_html('{userid} <sup>?</sup>', userid=obj.user_id)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user')
        qs = qs.only(
                *[f.name for f in UserBrowser._meta.fields],
                'user__id', 'user__username')
        return qs

    def get_fields(self, request, obj=None):
        return (
            ('user' if obj is None else 'user_link',)
            + cast(tuple, self.fields)
            + (('added_on',) if obj is not None else ())
        )

    def has_change_permission(self, request, obj=None):
        return False

    def get_form(self, request, *args, **kwargs):
        form = super().get_form(request, *args, **kwargs)
        if form.base_fields:
            form.base_fields['user_agent_string'].widget.attrs['style'] = "width: 50em;"
        return form
