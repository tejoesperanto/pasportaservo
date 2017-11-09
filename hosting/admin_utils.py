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


class SimpleBooleanListFilter(admin.SimpleListFilter):
    def lookups(self, request, model_admin):
        self.model = model_admin.model
        return ((1, _('Yes')), (0, _('No')))

    def is_no(self):
        return int(self.value()) == 0

    def queryset(self, request, queryset):
        if str(self.value()).isdigit():
            return self.perform_filter(queryset)


class SupervisorFilter(SimpleBooleanListFilter):
    title = _("supervisor status")
    parameter_name = 'is_supervisor'

    def perform_filter(self, queryset):
        country_filter = r'^[A-Z]{2}$'
        if self.is_no():
            return queryset.exclude(groups__name__regex=country_filter)
        else:
            return queryset.filter(groups__name__regex=country_filter).distinct()


class EmailValidityFilter(SimpleBooleanListFilter):
    title = _("invalid email")
    parameter_name = 'email_invalid'

    def perform_filter(self, queryset):
        from .models import Profile
        email_filter = {
            '{0}email__startswith'.format('user__' if self.model is Profile else ''): settings.INVALID_PREFIX,
        }
        if self.is_no():
            qs = queryset.exclude(**email_filter)
            if self.model is Profile:
                qs = qs.exclude(user__isnull=True)
            return qs
        else:
            return queryset.filter(**email_filter)


class ProfileHasUserFilter(SimpleBooleanListFilter):
    title = _("user is defined")
    parameter_name = 'has_user'

    def perform_filter(self, queryset):
        return queryset.filter(user__isnull=self.is_no())


class PlaceHasLocationFilter(SimpleBooleanListFilter):
    title = _("location is defined")
    parameter_name = 'has_location'

    def perform_filter(self, queryset):
        return queryset.filter(location__isnull=self.is_no())
