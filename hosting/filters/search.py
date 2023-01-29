from django import forms
from django.db import models

import django_filters as filters

from ..forms import SearchForm
from ..models import Condition, Place


class NumberOrNoneFilter(filters.NumberFilter):
    """
    Allows NULL values as the result of the filter.
    """
    def filter(self, qs, value):
        # If value is considered empty, no need to filter.
        if value in filters.constants.EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        # Query the numerical model field either by the
        # requested lookup (e.g., `gt`) or by being null.
        combined_query = (
            models.Q(**{f'{self.field_name}__{self.lookup_expr}': value})
            | models.Q(**{f'{self.field_name}__isnull': True})
        )
        return self.get_method(qs)(combined_query)


class ModelMultipleChoiceExcludeFilter(filters.ModelMultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('exclude', True)
        kwargs.setdefault('lookup_expr', 'in')
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        # No point in filtering if filter is empty.
        if not value:
            return qs
        return super().filter(qs, [tuple(value)])


class SearchFilterSet(filters.FilterSet):
    class Meta:
        model = Place
        form = SearchForm
        fields = (
            'owner__first_name', 'owner__last_name',
            'available',
            'max_guest', 'max_night',
            'tour_guide', 'have_a_drink',
            'contact_before',
        )
        filter_overrides = {
            models.BooleanField: {
                'filter_class': filters.BooleanFilter,
                'extra': lambda f: {
                    'widget': forms.CheckboxInput,
                },
            },
            models.CharField: {
                # Applicable to 'first_name' and 'last_name'.
                'filter_class': filters.CharFilter,
                'extra': lambda f: {
                    'lookup_expr': 'unaccent__icontains',
                },
            },
            models.IntegerField: {
                # Applicable to 'max_guest' and 'max_night'.
                'filter_class': NumberOrNoneFilter,
                'extra': lambda f: {
                    'lookup_expr': 'gte',
                },
            },
            models.PositiveSmallIntegerField: {
                # Applicable to 'contact_before'.
                'filter_class': NumberOrNoneFilter,
                'extra': lambda f: {
                    'lookup_expr': 'lte',
                },
            },
        }

    # Include only hosts who offer specific facilitations...
    facilitations = filters.ModelMultipleChoiceFilter(
        field_name='conditions',
        conjoined=True,
        queryset=(
            Condition.objects.filter(restriction=False).order_by(Condition.active_name_field())
        ))

    # Exclude hosts who indicated specific restrictions...
    restrictions = ModelMultipleChoiceExcludeFilter(
        field_name='conditions',
        queryset=(
            Condition.objects.filter(restriction=True).order_by(Condition.active_name_field())
        ))

    def __init__(self, data=None, *args, **kwargs):
        if data is None:
            # By default, available places are looked up.
            data = {'available': True}
        super().__init__(data, *args, **kwargs)

    def get_form_class(self):
        # Inject the model reference into the form, because it lacks an
        # Options object (`_meta`) with this reference.
        form_class = super().get_form_class()
        form_class.model = self._meta.model
        return form_class

    def filter_queryset(self, queryset):
        # TODO filter usernames by fname or lname...
        return super().filter_queryset(queryset)
