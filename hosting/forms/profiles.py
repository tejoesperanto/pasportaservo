from copy import deepcopy

from django import forms
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper

from core.models import SiteConfiguration

from ..models import Preferences, Profile
from ..utils import value_without_invalid_marker
from ..validators import TooNearPastValidator, client_side_validated
from ..widgets import ClearableWithPreviewImageInput, InlineRadios


@client_side_validated
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'title',
            'first_name',
            'last_name',
            'names_inversed',
            'gender', 'pronoun',
            'birth_date',
            'description',
            'avatar',
        ]
        widgets = {
            'names_inversed': forms.RadioSelect(choices=((False, _("First, then Last")),
                                                         (True, _("Last, then First"))),),
            'avatar': ClearableWithPreviewImageInput,
        }

    class _validation_meta:
        offer_required_fields = ['birth_date']
        book_required_fields = ['first_name', 'last_name', 'gender', 'birth_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = SiteConfiguration.get_solo()
        self.helper = FormHelper(self)
        self.fields['first_name'].widget.attrs['inputmode'] = 'latin-name'
        self.fields['last_name'].widget.attrs['inputmode'] = 'latin-name'
        self.fields['names_inversed'].label = _("Names ordering")
        self.helper['names_inversed'].wrap(InlineRadios, radio_label_class='person-full-name')

        field_bd = self.fields['birth_date']
        if self.instance.has_places_for_hosting or self.instance.has_places_for_meeting:
            if self.instance.has_places_for_hosting:
                message = _("The minimum age to be allowed hosting is {age:d}.")
                allowed_age = config.host_min_age
            else:
                message = _("The minimum age to be allowed meeting with visitors is {age:d}.")
                allowed_age = config.meet_min_age
            message = format_lazy(message, age=allowed_age)
            field_bd.required = True
            field_bd.validators.append(TooNearPastValidator(allowed_age))
            # We have to manually create a copy of the error messages dict because Django does not do it:
            # https://code.djangoproject.com/ticket/30839#ticket
            field_bd.error_messages = deepcopy(field_bd.error_messages)
            field_bd.error_messages['max_value'] = message
        field_bd.widget.attrs['placeholder'] = 'jjjj-mm-tt'
        field_bd.widget.attrs['data-date-end-date'] = '0d'
        field_bd.widget.attrs['pattern'] = '[1-2][0-9]{3}-((0[1-9])|(1[0-2]))-((0[1-9])|([12][0-9])|(3[0-1]))'

        if self.instance.has_places_for_in_book:
            message = _("This field is required to be printed in the book.")
            for field in self._validation_meta.book_required_fields:
                req_field = self.fields[field]
                req_field.required = True
                # We have to manually create a copy of the error messages dict because Django does not do it:
                # https://code.djangoproject.com/ticket/30839#ticket
                req_field.error_messages = deepcopy(req_field.error_messages)
                req_field.error_messages['required'] = message
                req_field.widget.attrs['data-error-required'] = message

        self.fields['avatar'].widget.attrs['accept'] = 'image/*'

    def clean_avatar(self):
        try:
            self.cleaned_data['avatar'].file
        except AttributeError:
            pass
        except IOError:
            raise forms.ValidationError(
                _("There seems to be a problem with the avatar's file. "
                  "Please re-upload it or choose '%(label)s'."),
                code='faulty_binary',
                params={'label': self.fields['avatar'].widget.clear_checkbox_label})
        return self.cleaned_data['avatar']

    def clean(self):
        """
        Sets specific fields as required when user wants their data to be
        printed in the paper edition.
        """
        cleaned_data = super().clean()
        profile = self.instance

        has_offer = profile.has_places_for_accepting_guests
        names_filled = any([cleaned_data.get(field, False) for field in ('first_name', 'last_name')])
        for_book = profile.has_places_for_in_book
        all_filled = all([
            cleaned_data.get(field, False)
            for field in self._validation_meta.book_required_fields
        ])

        if has_offer and not for_book and not names_filled:
            message = _("Please indicate how guests should name you")
            raise forms.ValidationError(message)

        if for_book and not all_filled:
            message = _("You want to be in the printed edition of Pasporta Servo. "
                        "In order to have a quality product, some fields are required. "
                        "If you think there is a problem, please contact us.")
            if profile.has_places_for_hosting != profile.has_places_for_in_book:
                clarify_message = format_lazy(
                    _("You are a host in {count_as_host} places, "
                      "of which {count_for_book} should be in the printed edition."),
                    count_as_host=profile.has_places_for_accepting_guests,
                    count_for_book=profile.has_places_for_in_book)
                raise forms.ValidationError([message, clarify_message])
            else:
                raise forms.ValidationError(message)

        if profile.death_date and 'birth_date' in cleaned_data:
            if cleaned_data['birth_date'] > profile.death_date:
                # Sanity check for life dates congruence.
                # xgettext:python-brace-format
                field_bd_message = _("The indicated date of birth is in conflict "
                                     "with the date of death ({:%Y-%m-%d}).")
                self.add_error(
                    'birth_date', format_lazy(field_bd_message, profile.death_date)
                )

        return cleaned_data


class ProfileCreateForm(ProfileForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user = self.user
        profile.email = self.user.email
        if commit:
            profile.save()
        return profile
    save.alters_data = True


class ProfileEmailUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['email']
        error_messages = {
            'email': {
                'max_length': _(
                    "Ensure that this value has at most %(limit_value)d characters "
                    "(it has now %(show_value)d)."
                ),
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Displays a clean value of the address in the form.
        self.initial['email'] = value_without_invalid_marker(self.instance.email)

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save(update_fields=['email', 'modified'])
        return profile
    save.alters_data = True


class PreferenceOptinsForm(forms.ModelForm):
    class Meta:
        model = Preferences
        fields = [
            'public_listing',
            'site_analytics_consent',
        ]
        widgets = {
            'site_analytics_consent': forms.CheckboxInput
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget_settings = {
            'data-on-ajax-success': 'updatePrivacyResult',
            'data-on-ajax-error': 'updatePrivacyFailure',
            # autocomplete attribute is required for Firefox to drop
            # caching and refresh the checkbox on each page reload.
            'autocomplete': 'off',
        }
        widget_classes = ' ajax-on-change'
        for field in self._meta.fields:
            attrs = self.fields[field].widget.attrs
            attrs.update(widget_settings)
            attrs['class'] = attrs.get('class', '') + widget_classes
            attrs['data-initial'] = self[field].value()
        self.helper = FormHelper(self)
