from abc import ABC, abstractmethod
from typing import cast

from django.conf import settings
from django.contrib import admin
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from core.utils import camel_case_split

from ..models import PasportaServoUser, Place, Profile, VisibilitySettings


class CountryMentionedOnlyFilter(admin.SimpleListFilter):
    title = _("country")
    parameter_name = 'country__in'

    def lookups(self, request, model_admin):
        self.multicountry = hasattr(model_admin.model, 'countries')
        country_field = 'countries' if self.multicountry else 'country'
        qs = model_admin.get_queryset(request).only(country_field).select_related(None)
        qs.query.annotations.clear()
        countries = [
            (country.code, country.name)
            for obj in qs
            for country in (obj.countries if self.multicountry else [obj.country])
        ]
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
            if current_lookups:
                query_string = changelist.get_query_string(
                    new_params={self.parameter_name: ",".join(current_lookups)},
                    remove=[])
            else:
                query_string = changelist.get_query_string(
                    new_params={},
                    remove=[self.parameter_name])
            yield {
                'selected': item_selected,
                'query_string': query_string,
                'display': title,
            }

    def queryset(self, request, queryset):
        value_list = set([
            v.strip()
            for v in self.values()
            if len(v.strip()) == 2 and v.strip().isalpha()
        ])
        if not self.multicountry:
            lookup = Q(country__in=value_list)
        else:
            # No risk of injection because values are restricted to be 2 letters.
            lookup = Q(countries__regex=r'(^|,)({})(,|$)'.format('|'.join(value_list)))
        if value_list:
            return queryset.filter(lookup)
        else:
            return queryset.none() if self.value() else queryset


class VisibilityTargetFilter(admin.SimpleListFilter):
    title = _("type")
    parameter_name = 'model_type'

    def lookups(self, request, model_admin):
        targets = [
            (model, _(user_friendly_model.lower()))
            for model, user_friendly_model in [
                (model_type, " ".join(camel_case_split(model_type)))
                for model_type in VisibilitySettings.specific_models().keys()
            ]
        ]
        targets.sort(key=lambda target: target[1])
        return targets

    def queryset(self, request, queryset):
        return queryset.filter(model_type=self.value()) if self.value() else queryset


class SimpleBooleanListFilter(ABC, admin.SimpleListFilter):
    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin):
        self.model = model_admin.model
        return ((1, _('Yes')), (0, _('No')))

    @abstractmethod
    def perform_filter(self, queryset: QuerySet):
        ...

    def is_no(self):
        # Called from `perform_filter` only, after verifying that the value is
        # a digit in string format (and not None).
        return int(cast(str, self.value())) == 0

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        if str(self.value()).isdigit():
            return self.perform_filter(queryset)


class SupervisorFilter(SimpleBooleanListFilter):
    title = _("supervisor status")
    parameter_name = 'is_supervisor'

    def perform_filter(self, queryset: QuerySet[PasportaServoUser]):
        country_filter = r'^[A-Z]{2}$'
        if self.is_no():
            return queryset.exclude(groups__name__regex=country_filter)
        else:
            return queryset.filter(groups__name__regex=country_filter).distinct()


class EmailValidityFilter(SimpleBooleanListFilter):
    title = _("invalid email")
    parameter_name = 'email_invalid'

    def perform_filter(self, queryset):
        parent_model = 'user__' if self.model is Profile else ''
        email_filter = {
            f'{parent_model}email__startswith': settings.INVALID_PREFIX,
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

    def perform_filter(self, queryset: QuerySet[Profile]):
        return queryset.filter(user__isnull=self.is_no())


class PlaceHasLocationFilter(SimpleBooleanListFilter):
    title = _("location is defined")
    parameter_name = 'has_location'

    def perform_filter(self, queryset: QuerySet[Place]):
        return queryset.filter(location__isnull=self.is_no())


class ActiveStatusFilter(SimpleBooleanListFilter):
    title = _("active")
    parameter_name = 'is_active'

    def perform_filter(self, queryset):
        return queryset.filter(is_active=not self.is_no())
