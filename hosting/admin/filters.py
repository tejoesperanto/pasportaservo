from enum import Enum

from django.conf import settings
from django.contrib import admin
from django.db.models import Q
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from core.utils import camel_case_split

from ..models import Profile, VisibilitySettings


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


class YearBracketFilter(admin.DateFieldListFilter):
    class Brackets(str, Enum):
        EXACT = 'exact'
        SINCE = 'since'
        UNTIL = 'until'

    @classmethod
    def configure(cls, bracket=Brackets.EXACT):
        if bracket not in (cls.Brackets.SINCE, cls.Brackets.UNTIL):
            bracket = cls.Brackets.EXACT
        return type(
            f'YearBracket{bracket.capitalize()}Filter',
            (cls,),
            {
                'bracket': bracket,
            }
        )

    def __init__(self, field, request, params, model, model_admin, field_path):
        original_field_path = field_path
        field_path = f'{field_path}__year'
        super().__init__(field, request, params, model, model_admin, field_path)
        qs = (
            model_admin
            .get_queryset(request)
            .select_related(None)
            .order_by(f'-{original_field_path}')
            .only(field_path)
        )
        qs.query.annotations.clear()
        all_years = list(dict.fromkeys(qs.values_list(field_path, flat=True)))
        if not hasattr(self, 'bracket'):
            self.bracket = self.Brackets.EXACT
        self.links = (
            (_('Any year'), {}),
        )
        lookup_kwarg = ''
        if self.bracket is self.Brackets.SINCE:
            label_string = _("from %(date)s")
            self.lookup_kwarg_since = self.field_generic + 'gte'
            lookup_kwarg = self.lookup_kwarg_since
        if self.bracket is self.Brackets.UNTIL:
            label_string = _("until %(date)s")
            self.lookup_kwarg_until = self.field_generic + 'lte'
            lookup_kwarg = self.lookup_kwarg_until
        if self.bracket is self.Brackets.EXACT:
            self.links += tuple(
                (str(year), {
                    self.lookup_kwarg_since: str(year),
                    self.lookup_kwarg_until: str(year + 1),
                })
                for year in all_years if year is not None
            )
        else:
            def label(year):
                return lazy(
                    lambda date=year: (label_string % {'date': date}).capitalize(),
                    str)
            self.links += tuple(
                (label(year), {lookup_kwarg: str(year)})
                for year in all_years if year is not None
            )
        if field.null:
            self.links += (
                (_('No date'), {self.lookup_kwarg_isnull: str(True)}),
                (_('Has date'), {self.lookup_kwarg_isnull: str(False)}),
            )


class DependentFieldFilter(admin.SimpleListFilter):
    @classmethod
    def configure(cls, field, related_field, coerce=None, sort=False, sort_reverse=None):
        if coerce is None or not callable(coerce):
            coerce = lambda v: v
        return type(
            ''.join(related_field.split('_')).capitalize()
            + 'Per' + ''.join(field.split('_')).capitalize()
            + 'Filter',
            (cls,),
            {
                'origin_field': field,
                'related_field': related_field,
                'parameter_name': related_field,
                'coerce_value': lambda filter, value: coerce(value),
                'sorting': {
                    'enabled': sort,
                    'reverse': sort_reverse,
                },
            }
        )

    def lookups(self, request, model_admin):
        qs = (
            model_admin.model._default_manager.all()
            .filter(**{self.origin_field: self.dependent_on_value})
        )
        all_values = map(
            self.coerce_value,
            qs.values_list(self.related_field, flat=True).distinct())
        if self.sorting['enabled']:
            all_values = sorted(all_values, reverse=self.sorting['reverse'])
        for val in all_values:
            yield (val, str(val))

    def has_output(self):
        return bool(self.dependent_on_value)

    def value(self):
        val = self.used_parameters.get(self.parameter_name)
        if val in (ch[0] for ch in self.lookup_choices):
            return val
        else:
            return None

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{self.parameter_name: self.value()})
        else:
            return queryset

    def __init__(self, request, params, model, model_admin):
        self.title = model._meta.get_field(self.related_field).verbose_name
        self.dependent_on_value = request.GET.get(self.origin_field)
        super().__init__(request, params, model, model_admin)


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

    def perform_filter(self, queryset):
        return queryset.filter(user__isnull=self.is_no())


class PlaceHasLocationFilter(SimpleBooleanListFilter):
    title = _("location is defined")
    parameter_name = 'has_location'

    def perform_filter(self, queryset):
        return queryset.filter(location__isnull=self.is_no())


class ActiveStatusFilter(SimpleBooleanListFilter):
    title = _("active")
    parameter_name = 'is_active'

    def perform_filter(self, queryset):
        return queryset.filter(is_active=not self.is_no())
