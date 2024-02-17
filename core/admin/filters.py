from enum import Enum
from typing import Callable, Optional, TypedDict, cast

from django.contrib import admin
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _


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
    origin_field: str
    related_field: str
    parameter_name: str
    coerce_value: Callable
    SortConfig = TypedDict('SortConfig', {'enabled': bool, 'reverse': bool})
    sorting: SortConfig

    @classmethod
    def configure(
            cls,
            field: str,
            related_field: str,
            coerce: Optional[Callable] = None,
            sort: bool = False,
            sort_reverse: Optional[bool] = None,
    ):
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
                    'enabled': bool(sort),
                    'reverse': bool(sort_reverse),
                },
            }
        )

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin):
        qs = (
            cast(type[Model], model_admin.model)._default_manager.all()
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

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        if self.value():
            return queryset.filter(**{self.parameter_name: self.value()})
        else:
            return queryset

    def __init__(
            self,
            request: HttpRequest,
            params: dict[str, str],
            model: type[Model],
            model_admin: admin.ModelAdmin,
    ):
        self.title = model._meta.get_field(self.related_field).verbose_name
        self.dependent_on_value = request.GET.get(self.origin_field)
        super().__init__(request, params, model, model_admin)
