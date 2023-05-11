from django import forms
from django.core import checks
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
)
from django.utils.html import format_html
from django.utils.itercompat import is_iterable
from django.utils.translation import gettext_lazy as _

from phonenumber_field.modelfields import (
    PhoneNumberField as DjangoPhoneNumberField,
)

from .widgets import MultiNullBooleanSelects, TextWithDatalistInput


class StyledEmailField(models.EmailField):
    @property
    def icon(self):
        template = ('<span class="fa fa-envelope" title="{title}" '
                    '      data-toggle="tooltip" data-placement="bottom"></span>')
        return format_html(template, title=_("email address").capitalize())


class PhoneNumberField(DjangoPhoneNumberField):
    default_error_messages = {'invalid': _("Enter a valid phone number.")}


class RangeIntegerField(models.IntegerField):
    description = _("Integer within a predefined range")

    def __init__(self, *args, min_value=None, max_value=None, **kwargs):
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


def SuggestiveField(verbose_name=None, choices=None, to_field=None, **kwargs):
    if isinstance(choices, str) or isinstance(choices, models.base.ModelBase):
        # Assumed to be a reference to a model.
        return ForeigKeyWithSuggestions(
            choices=choices, to_field=to_field,
            verbose_name=verbose_name,
            **kwargs)
    else:
        # Otherwise it is a list of options.
        return CharFieldWithSuggestions(
            choices=choices,
            verbose_name=verbose_name,
            **kwargs)


def _handle_invalid_choice(field, *args, function='validate', code='invalid_choice'):
    validation_exception_intercepted = False
    try:
        validation_result = getattr(super(type(field), field), function)(*args)
    except forms.ValidationError as exception:
        validation_exception_intercepted = True
        validation_result = None
        exception.error_list = [err for err in exception.error_list if err.code != code]
        if exception.error_list:
            raise exception
    return (validation_result, validation_exception_intercepted)


class CharFieldWithSuggestions(models.CharField):
    def __init__(self, verbose_name=None, choices=None, **kwargs):
        kwargs['verbose_name'] = verbose_name
        super().__init__(**kwargs)
        self.suggestions = choices
        if not isinstance(choices, str) and is_iterable(choices):
            choices = [('{:03d}'.format(i), choice)
                       if isinstance(choice, str) or not is_iterable(choice)
                       else choice
                       for i, choice in enumerate(choices, start=1)]
        self.choices = choices

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


class ForeigKeyWithSuggestions(models.ForeignKey):
    def __init__(self, verbose_name=None, choices=None, to_field=None, **kwargs):
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
        def get_object(self, model_instance):
            try:
                return super().get_object(model_instance)
            except models.ObjectDoesNotExist:
                data = {'pk': -1}
                data[self.field.to_fields[0]] = getattr(model_instance, self.field.attname)
                return self.field.remote_field.model(**data)

    forward_related_accessor_class = LenientForwardDescriptor

    def validate(self, value, model_instance):
        _handle_invalid_choice(self, value, model_instance, code='invalid')

    def formfield(self, **kwargs):
        class SuggestiveModelChoiceFormField(forms.ModelChoiceField):
            widget = TextWithDatalistInput

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.empty_label = None

            def to_python(self, value):
                converted_value, is_invalid = _handle_invalid_choice(self, value, function='to_python')
                if is_invalid:
                    data = {'pk': value}
                    if self.to_field_name and self.to_field_name != 'pk':
                        data.update({self.to_field_name: value})
                        data['pk'] = -1
                    converted_value = self.queryset.model(**data)
                return converted_value

        defaults = {'form_class': SuggestiveModelChoiceFormField}
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
