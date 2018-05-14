from django import forms
from django.core import checks
from django.db import models
from django.utils import six
from django.utils.html import format_html
from django.utils.itercompat import is_iterable
from django.utils.translation import ugettext_lazy as _

from .widgets import TextWithDatalistInput


class StyledEmailField(models.EmailField):
    @property
    def icon(self):
        template = ('<span class="fa fa-envelope" title="{title}" '
                    '      data-toggle="tooltip" data-placement="bottom"></span>')
        return format_html(template, title=_("email address").capitalize())


def SuggestiveField(verbose_name=None, choices=None, to_field=None, **kwargs):
    if isinstance(choices, six.string_types) or isinstance(choices, models.base.ModelBase):
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
        if not isinstance(choices, six.string_types) and is_iterable(choices):
            choices = [('{:03d}'.format(i), choice)
                       if isinstance(choice, six.string_types) or not is_iterable(choice)
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
        if not isinstance(self.suggestions_source_field, six.string_types):
            errors.append(
                checks.Error(
                    "A SuggestiveField's 'to_field' attribute must be a string.",
                    obj=self,
                    id='fields.E170.3',
                )
            )
        return errors

    def get_attname(self):
        return '{}_value'.format(self.name)

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
