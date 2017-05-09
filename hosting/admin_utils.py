from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.utils.formats import date_format
from django.contrib.admin.utils import display_for_value
from django.conf import settings


class ShowConfirmedMixin(object):
    def display_confirmed(self, obj):
        return format_html(
            display_for_value(obj.confirmed_on is not None, None, boolean=True) +
            ("&nbsp; " + date_format(obj.confirmed_on, 'DATETIME_FORMAT', use_l10n=True)
            if obj.confirmed_on else ""))

    display_confirmed.short_description = _("confirmed on")
    display_confirmed.admin_order_field = 'confirmed_on'


class ShowDeletedMixin(object):
    def is_deleted(self, obj):
        return format_html("<span style='color:%(color)s'>%(content)s</span>" % {
            'color': "#666" if not obj.deleted else "#dd4646",
            'content': "&#x2718;" if not obj.deleted else "&#x2714;!",
        })

    is_deleted.short_description = _("deleted")
    is_deleted.admin_order_field = 'deleted'


class CountryMentionedOnlyFilter(admin.SimpleListFilter):
    title = _("country")
    parameter_name = 'country__in'

    def lookups(self, request, model_admin):
        countries = [(obj.country.code, obj.country.name) for obj in model_admin.get_queryset(request)]
        return sorted(set(countries), key=lambda country: country[1])

    def values(self):
        values = []
        if self.value():
            values = self.value().split(",")
        return values

    def choices(self, changelist):
        yield {
            'selected': not self.value(),
            'query_string': changelist.get_query_string({}, [self.parameter_name]),
            'display': _('All'),
        }
        value_list = self.values()
        for lookup, title in self.lookup_choices:
            current_lookups = set(value_list)
            item_selected = lookup in current_lookups
            if item_selected:
                current_lookups.remove(lookup)
            else:
                current_lookups.add(lookup)
            query_string = changelist.get_query_string(
                new_params={self.parameter_name: ",".join(current_lookups)} if current_lookups else {},
                remove=[self.parameter_name] if not current_lookups else [])
            yield {'selected': item_selected, 'query_string': query_string, 'display': title,}

    def queryset(self, request, queryset):
        value_list = set([v.strip() for v in self.values() if len(v.strip()) == 2])
        return queryset.filter(country__in=value_list) if value_list else queryset


class SupervisorFilter(admin.SimpleListFilter):
    title = _("supervisor status")
    parameter_name = 'is_supervisor'

    def lookups(self, request, model_admin):
        return ((1, _('Yes')), (0, _('No')))

    def queryset(self, request, queryset):
        if str(self.value()).isdigit():
            country_filter = r'^[A-Z]{2}$'
            if int(self.value()) == 0:
                return queryset.exclude(groups__name__regex=country_filter)
            else:
                return queryset.filter(groups__name__regex=country_filter)


class EmailValidityFilter(admin.SimpleListFilter):
    title = _("invalid email")
    parameter_name = 'email_invalid'

    def lookups(self, request, model_admin):
        return ((1, _('Yes')), (0, _('No')))

    def queryset(self, request, queryset):
        if str(self.value()).isdigit():
            if int(self.value()) == 0:
                return queryset.exclude(user__email__startswith=settings.INVALID_PREFIX).exclude(user__isnull=True)
            else:
                return queryset.filter(user__email__startswith=settings.INVALID_PREFIX)


class ProfileHasUserFilter(admin.SimpleListFilter):
    title = _("user is defined")
    parameter_name = 'has_user'

    def lookups(self, request, model_admin):
        return ((1, _('Yes')), (0, _('No')))

    def queryset(self, request, queryset):
        if str(self.value()).isdigit():
            return queryset.filter(user__isnull=(int(self.value()) == 0))

