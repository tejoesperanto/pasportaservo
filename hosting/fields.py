from typing import (
    TYPE_CHECKING, Any, Iterable, Literal, Optional, cast, overload, override,
)

from django import forms
from django.contrib.gis.db.models import (
    LineStringField as BuiltinLineStringField, PointField as BuiltinPointField,
)
from django.contrib.gis.geos import LineString, Point
from django.core import checks
from django.core.validators import (
    MaxLengthValidator, MaxValueValidator,
    MinValueValidator, ProhibitNullCharactersValidator,
)
from django.db import models
from django.db.models.fields.related import ForeignObject
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
)
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django_countries.fields import (
    Country, CountryField as ThirdPartyCountryField,
)
from phonenumber_field.modelfields import (
    PhoneNumber, PhoneNumberField as ThirdPartyPhoneNumberField,
)

from core.fields import SimpleAnnotationFieldMixin

from .widgets import MultiNullBooleanSelects, TextWithDatalistInput

if TYPE_CHECKING:
    from django.db.models.fields import _LiteralFieldChoices


class StyledEmailField(SimpleAnnotationFieldMixin[str], models.EmailField):
    @property
    def icon(self):
        template = ('<span class="fa fa-envelope" title="{title}" '
                    '      data-toggle="tooltip" data-placement="bottom"></span>')
        return format_html(template, title=_("email address").capitalize())


class PhoneNumberField(
        SimpleAnnotationFieldMixin[PhoneNumber], ThirdPartyPhoneNumberField,
):
    default_error_messages = {'invalid': _("Enter a valid phone number.")}
    region: Optional[str]


class CountryField[_C: (Country, list[Country])](
        SimpleAnnotationFieldMixin[_C], ThirdPartyCountryField,
):
    if TYPE_CHECKING:
        @overload
        def __new__(  # type: ignore[overload]
            cls, *args, multiple: Literal[True], **kwargs,
        ) -> 'CountryField[list[Country]]':
            ...

        @overload
        def __new__(
            cls, *args, multiple: Literal[False], **kwargs,
        ) -> 'CountryField[Country]':
            ...

        @overload
        def __new__(cls, *args, **kwargs) -> 'CountryField[Country]':
            ...


class PointField[_P: Point | None](SimpleAnnotationFieldMixin[_P], BuiltinPointField):
    if TYPE_CHECKING:
        @overload
        def __new__(  # type: ignore[overload]
                cls, *args, null: Literal[False], **kwargs,
        ) -> 'PointField[Point]':
            ...

        @overload
        def __new__(
                cls, *args, null: Literal[True], **kwargs,
        ) -> 'PointField[Point | None]':
            ...

        @overload
        def __new__(cls, *args, **kwargs) -> 'PointField[Point]':
            ...


class LineStringField(SimpleAnnotationFieldMixin[LineString], BuiltinLineStringField):
    pass


class RangeIntegerField[_I: int | None](
        models.IntegerField[_I] if TYPE_CHECKING else models.IntegerField
):
    description = _("Integer within a predefined range")

    if TYPE_CHECKING:
        @overload
        def __new__(  # type: ignore[overload]
                cls,
                *args,
                null: Literal[False],
                min_value: Optional[int | Any],
                max_value: Optional[int | Any],
                **kwargs,
        ) -> 'RangeIntegerField[int]':
            ...

        @overload
        def __new__(
                cls,
                *args,
                null: Literal[True],
                min_value: Optional[int | Any],
                max_value: Optional[int | Any],
                **kwargs,
        ) -> 'RangeIntegerField[int | None]':
            ...

        @overload
        def __new__(
                cls,
                *args,
                min_value: Optional[int | Any] = ...,
                max_value: Optional[int | Any] = ...,
                **kwargs,
        ) -> 'RangeIntegerField[int]':
            ...

    @override
    def __init__(
            self,
            *args,
            min_value: Optional[int | Any] = None, max_value: Optional[int | Any] = None,
            **kwargs,
    ):
        self.min_value, self.max_value = None, None
        super().__init__(*args, **kwargs)
        if isinstance(min_value, int):
            self.validators.append(MinValueValidator(min_value))
            self.min_value = min_value
        if isinstance(max_value, int):
            self.validators.append(MaxValueValidator(max_value))
            self.max_value = max_value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.min_value is not None:
            kwargs['min_value'] = self.min_value
        if self.max_value is not None:
            kwargs['max_value'] = self.max_value
        return name, path, args, kwargs

    def get_internal_type(self):
        return 'IntegerField'

    def formfield(self, **kwargs):
        return super().formfield(**{
            'min_value': self.min_value,
            'max_value': self.max_value,
            **kwargs,
        })


class SuggestiveField[_M: models.Model]:
    @overload
    def __new__(
            cls,
            verbose_name: Optional[str],
            choices: str | type[_M],
            **kwargs,
    ) -> 'ForeigKeyWithSuggestions[_M]':
        ...  # pragma: no cover

    @overload
    def __new__(
            cls,
            verbose_name: Optional[str],
            choices: '_LiteralFieldChoices',
            **kwargs,
    ) -> 'CharFieldWithSuggestions':
        ...  # pragma: no cover

    def __new__(
            cls,
            verbose_name: Optional[str] = None,
            choices: Optional['str | type[_M] | _LiteralFieldChoices'] = None,
            to_field: Optional[str] = None,
            **kwargs,
    ):
        if (isinstance(choices, str)
                or (isinstance(choices, type) and issubclass(choices, models.Model))):
            # Assumed to be a reference to a model.
            return ForeigKeyWithSuggestions[_M](
                choices=choices, to_field=to_field,
                verbose_name=verbose_name,
                **kwargs)
        else:
            # Otherwise it is a list of options.
            return CharFieldWithSuggestions(
                choices=choices,
                verbose_name=verbose_name,
                **kwargs)


def _handle_invalid_choice(
        field: models.Field | forms.Field,
        *args, function: str = 'validate', code: str = 'invalid_choice',
) -> tuple[Any, Literal[False]] | tuple[None, Literal[True]]:
    if isinstance(field, forms.Field):
        parent_field = super(type(field), field)
    else:
        parent_field = super(type(field), field)

    try:
        validation_result = getattr(parent_field, function)(*args)
    except forms.ValidationError as exception:
        validation_exception_intercepted = True
        exception.error_list = [
            err
            for err in cast(list[forms.ValidationError], getattr(exception, 'error_list', []))
            if err.code != code
        ]
        if exception.error_list:
            raise exception
        return (None, validation_exception_intercepted)
    else:
        return (validation_result, False)


class CharFieldWithSuggestions(models.CharField[str] if TYPE_CHECKING else models.CharField):
    if TYPE_CHECKING:
        def __new__(cls, *args, **kwargs) -> 'CharFieldWithSuggestions':
            ...

    def __init__(
            self,
            *,
            verbose_name: Optional[str] = None,
            choices: Optional['_LiteralFieldChoices'] = None,
            **kwargs,
    ):
        kwargs['verbose_name'] = verbose_name
        super().__init__(**kwargs)
        self.suggestions = choices
        if not isinstance(choices, str) and isinstance(choices, Iterable):
            choices = [('{:03d}'.format(i), choice)
                       if isinstance(choice, str) or not isinstance(choice, Iterable)
                       else choice
                       for i, choice in enumerate(choices, start=1)]
        self.choices: '_LiteralFieldChoices' = choices  # type: ignore[arg-type]

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['choices'] = self.suggestions
        return name, path, args, kwargs

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if self.suggestions is None:
            errors.append(
                checks.Error(
                    "A SuggestiveField must define a 'choices' attribute.",
                    obj=self,
                    id='fields.E170.1',
                )
            )
        for error in errors:
            error.msg = error.msg.replace('CharField', 'String-based SuggestiveField')
        return errors

    def get_choices(self, **kwargs):
        kwargs['include_blank'] = False
        return super().get_choices(**kwargs)

    def validate(self, value, model_instance):
        _handle_invalid_choice(self, value, model_instance)

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        try:
            value = {i: choice for (i, choice) in self.choices}[value]
        except KeyError:
            pass
        return value

    def formfield(self, **kwargs):
        class SuggestiveTypedChoiceFormField(forms.TypedChoiceField):
            widget = TextWithDatalistInput

            def to_python(self, value):
                value = super().to_python(value)
                if value not in self.empty_values:
                    try:
                        value = next(i for (i, choice) in self.choices if choice == value)
                    except StopIteration:
                        pass
                return value

            def validate(self, value):
                _handle_invalid_choice(self, value)

        defaults = {'choices_form_class': SuggestiveTypedChoiceFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class ForeigKeyWithSuggestions[_M: models.Model](
        models.ForeignKey[_M] if TYPE_CHECKING else models.ForeignKey
):
    if TYPE_CHECKING:
        def __new__(cls, *args, **kwargs) -> 'ForeigKeyWithSuggestions[_M]':
            ...

    def __init__(
            self,
            *,
            verbose_name: Optional[str] = None,
            choices: Optional[type[_M] | str] = None,
            to_field: Optional[str] = None,
            **kwargs,
    ):
        self.suggestions_source_field = to_field
        self.suggestions = choices
        kwargs.update(
            db_constraint=False, null=True, on_delete=models.DO_NOTHING,
            to=self.suggestions, to_field=to_field, verbose_name=verbose_name)
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        for provided_key in ('to', 'db_constraint', 'null', 'on_delete'):
            del kwargs[provided_key]
        kwargs['choices'] = self.suggestions
        return name, path, args, kwargs

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if not self.suggestions_source_field:
            errors.append(
                checks.Error(
                    "A SuggestiveField must define a 'to_field' attribute.",
                    obj=self,
                    id='fields.E170.2',
                )
            )
        if not isinstance(self.suggestions_source_field, str):
            errors.append(
                checks.Error(
                    "A SuggestiveField's 'to_field' attribute must be a string.",
                    obj=self,
                    id='fields.E170.3',
                )
            )
        return errors

    class LenientForwardDescriptor(ForwardManyToOneDescriptor):
        field: 'ForeignObject[_M]'

        def get_object(self, model_instance: _M):
            try:
                return super().get_object(model_instance)
            except models.ObjectDoesNotExist:  # type: ignore[attr-defined]
                data = {'pk': -1}
                data[self.field.to_fields[0]] = getattr(model_instance, self.field.attname)
                return self.field.remote_field.model(**data)

    forward_related_accessor_class = LenientForwardDescriptor

    def validate(self, value, model_instance):
        _handle_invalid_choice(self, value, model_instance, code='invalid')

    def formfield(self, **kwargs):
        class SuggestiveModelChoiceFormField(forms.ModelChoiceField):
            widget = TextWithDatalistInput

            def __init__(self, *args, max_length=None, **kwargs):
                super().__init__(*args, **kwargs)
                self.empty_label = None

                def configure_validator(validator):
                    return (
                        lambda value:
                        validator(getattr(value, self.to_field_name or 'pk'))
                    )
                if max_length is not None and str(max_length).isdigit():
                    self.validators.append(
                        configure_validator(MaxLengthValidator(int(max_length))))
                self.validators.append(
                    configure_validator(ProhibitNullCharactersValidator()))

            def to_python(self, value):
                converted_value, is_invalid = _handle_invalid_choice(self, value, function='to_python')
                if is_invalid:
                    data = {'pk': value}
                    if self.to_field_name and self.to_field_name != 'pk':
                        data.update({self.to_field_name: value})
                        data['pk'] = -1
                    converted_value = self.queryset.model(**data)
                return converted_value

        defaults = {
            'form_class': SuggestiveModelChoiceFormField,
            'max_length': getattr(self.target_field, 'max_length', None),
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class MultiNullBooleanFormField(forms.MultiValueField):
    widget = MultiNullBooleanSelects

    def __init__(
            self, base_field, boolean_choices, *args,
            label_prefix=lambda choice: None, **kwargs,
    ):
        self.choices = list(base_field.choices)
        if isinstance(base_field.choices, forms.models.ModelChoiceIterator):
            self._single_choice_value = lambda choice: choice.value
        else:
            self._single_choice_value = lambda choice: choice
        field_labels = {
            self._single_choice_value(choice_value):
                (choice_label, label_prefix(choice_value))
            for choice_value, choice_label in self.choices
        }
        fields = [
            forms.NullBooleanField(label=choice_label, required=False)
            for _, choice_label in self.choices
        ]
        super().__init__(
            fields,
            *args,
            required=base_field.required,
            require_all_fields=False,
            widget=self.widget(field_labels, boolean_choices),
            **kwargs)
        self.empty_values = list(v for v in self.empty_values if v is not None)

    def compress(self, data_list):
        if not data_list:
            data_list = [None] * len(self.choices)
        # Each value of the data_list corresponds to a field.
        return zip(
            [self._single_choice_value(choice_value) for choice_value, _ in self.choices],
            data_list
        )
