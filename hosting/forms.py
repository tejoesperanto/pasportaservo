from datetime import date

from django import forms
# from django.contrib.gis.forms import OSMWidget
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django_countries.data import COUNTRIES

from core.models import SiteConfiguration
from maps.widgets import MapboxGlWidget

from .models import Profile, Place, Phone
from .utils import geocode
from .validators import TooNearPastValidator, client_side_validated
from .widgets import ClearableWithPreviewImageInput
from .utils import value_without_invalid_marker

User = get_user_model()


@client_side_validated
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'title',
            'first_name',
            'last_name',
            'names_inversed',
            'birth_date',
            'description',
            'avatar',
        ]
        widgets = {
            'names_inversed': forms.RadioSelect(choices=((False, _("First, then Last")),
                                                         (True, _("Last, then First"))),
                                                attrs={'class': 'form-control-horizontal'}),
            'avatar': ClearableWithPreviewImageInput,
        }

    class _validation_meta:
        book_required_fields = ['title', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = SiteConfiguration.get_solo()
        self.fields['first_name'].widget.attrs['inputmode'] = 'latin-name'
        self.fields['last_name'].widget.attrs['inputmode'] = 'latin-name'
        self.fields['names_inversed'].label = _("Names ordering")

        field_bd = self.fields['birth_date']
        if hasattr(self, 'instance') and (self.instance.is_hosting or self.instance.is_meeting):
            if self.instance.is_hosting:
                message = _("The minimum age to be allowed hosting is {age:d}.")
                allowed_age = config.host_min_age
            else:
                message = _("The minimum age to be allowed meeting with visitors is {age:d}.")
                allowed_age = config.meet_min_age
            message = format_lazy(message, age=allowed_age)
            field_bd.required = True
            field_bd.validators.append(TooNearPastValidator(allowed_age))
            field_bd.error_messages['max_value'] = message
        field_bd.widget.attrs['placeholder'] = 'jjjj-mm-tt'
        field_bd.widget.attrs['data-date-end-date'] = '0d'
        field_bd.widget.attrs['pattern'] = '[1-2][0-9]{3}-((0[1-9])|(1[0-2]))-((0[1-9])|([12][0-9])|(3[0-1]))'

        if hasattr(self, 'instance') and self.instance.is_in_book:
            message = _("This field is required to be printed in the book.")
            for field in self._validation_meta.book_required_fields:
                req_field = self.fields[field]
                req_field.required = True
                req_field.error_messages['required'] = message
                req_field.widget.attrs['data-error-required'] = message

        self.fields['avatar'].widget.attrs['accept'] = 'image/*'

    def clean(self):
        """Sets some fields as required if user wants their data to be printed in book."""
        cleaned_data = super().clean()
        if hasattr(self, 'instance'):
            profile = self.instance
            in_book = profile.is_in_book
            all_filled = all([cleaned_data.get(field, False) for field in self._validation_meta.book_required_fields])
            message = _("You want to be in the printed edition of Pasporta Servo. "
                        "In order to have a quality product, some fields are required. "
                        "If you think there is a problem, please contact us.")

            if in_book and not all_filled:
                # msg = _("This field is required to be printed in the book.")
                # for field in self._validation_meta.book_required_fields:
                #     if not cleaned_data.get(field, False):
                #         self.add_error(field, msg)
                raise forms.ValidationError(message)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Displays a clean value of the address in the form.
        self.initial['email'] = value_without_invalid_marker(self.instance.email)


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = [
            'country',
            'state_province',
            'postcode',
            'city',
            'address',
            'closest_city',
            'max_guest', 'max_night', 'contact_before',
            'description', 'short_description',
            'available',
            'tour_guide', 'have_a_drink',
            'sporadic_presence',
            'in_book',
            'conditions',
        ]
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 3}),
        }

    class _validation_meta:
        book_required_fields = [
            'address', 'city', 'closest_city', 'country', 'available',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].widget.attrs['rows'] = 2
        self.fields['conditions'].help_text = ""
        self.fields['conditions'].widget.attrs['data-placeholder'] = _("Choose your conditions...")

    def clean(self):
        cleaned_data = super().clean()
        config = SiteConfiguration.get_solo()

        # Verifies that user is of correct age if they want to host or meet guests.
        is_hosting = cleaned_data['available']
        is_meeting = cleaned_data['tour_guide'] or cleaned_data['have_a_drink']
        if any([is_hosting, is_meeting]):
            profile = self.profile if hasattr(self, 'profile') else self.instance.owner
            try:
                allowed_age = config.host_min_age if is_hosting else config.meet_min_age
                TooNearPastValidator(allowed_age)(profile.birth_date or date.today())
            except forms.ValidationError:
                if is_hosting:
                    self.add_error('available', "")
                    message = _("The minimum age to be allowed hosting is {age:d}.")
                else:
                    if cleaned_data['tour_guide']:
                        self.add_error('tour_guide', "")
                    if cleaned_data['have_a_drink']:
                        self.add_error('have_a_drink', "")
                    message = _("The minimum age to be allowed meeting with visitors is {age:d}.")
                raise forms.ValidationError(format_lazy(message, age=allowed_age))

        # Sets some fields as required if user wants their data to be printed in book.
        all_filled = all([cleaned_data.get(field, False) for field in self._validation_meta.book_required_fields])
        message = _("You want to be in the printed edition of Pasporta Servo. "
                    "In order to have a quality product, some fields are required. "
                    "If you think there is a problem, please contact us.")

        if cleaned_data['in_book'] and not all_filled:
            for field in self._validation_meta.book_required_fields:
                if not cleaned_data.get(field, False):
                    self.add_error(field, _("This field is required to be printed in the book."))
            raise forms.ValidationError(message)

        return cleaned_data

    def format_address(self):
        address = {
            'street': self.cleaned_data.get('address'),
            'zip': self.cleaned_data.get('postcode').replace(' ', ''),
            'city': self.cleaned_data.get('city'),
            'state': self.cleaned_data.get('state_province'),
            'country': COUNTRIES[self.cleaned_data.get('country')],
        }
        return '{street}, {zip} {city}, {state}, {country}'.format(**address)

    def save(self, commit=True):
        place = super().save(commit=False)
        location = geocode(self.format_address())
        if location.point and location.confidence > 1:
            # https://geocoder.opencagedata.com/api#confidence
            place.location = location.point
        if commit:
            place.save()
        self.confidence = location.confidence or 0
        return place
    save.alters_data = True


class PlaceCreateForm(PlaceForm):
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        place = super().save(commit=False)
        place.owner = self.profile
        if commit:
            place.save()
        return place
    save.alters_data = True


class PlaceLocationForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['location']
        widgets = {
            'location': MapboxGlWidget(),
            # 'location': OSMWidget(attrs={'template_name': "gis/openlayers-osm-custom.html", 'display_raw': True, 'map_width': "100%", 'map_height': "500px"}),  # noqa: E501
        }


class PlaceBlockForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['blocked_from', 'blocked_until']
    dirty = forms.ChoiceField(choices=(('blocked_from', 1), ('blocked_until', 2)),
                              widget=forms.HiddenInput, label="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget_settings = {
            'data-date-start-date': '-0d',
            'data-date-force-parse': 'false',
            'data-date-autoclose': 'true',
            'placeholder': 'jjjj-mm-tt',
            'data-on-ajax-setup': 'blockPlaceSetup',
            'data-on-ajax-success': 'blockPlaceSuccess',
        }
        widget_classes = ' form-control input-sm ajax-on-change'

        for (field_name, field_label) in (('blocked_from', _("commencing on")),
                                          ('blocked_until', _("concluding on"))):
            field = self.fields[field_name]
            field.label = field_label
            attrs = field.widget.attrs
            attrs.update(widget_settings)
            attrs['class'] = attrs.get('class', '') + widget_classes
            value = self[field_name].value()
            attrs['data-value'] = field.widget.format_value(value) if value is not None else ''

    def clean(self):
        """Checks if starting date is earlier then the ending date."""
        cleaned_data = super().clean()
        cleaned_data = dict((k, v) for k, v in cleaned_data.items()
                            if k == cleaned_data.get('dirty', ''))

        today = date.today()
        if (cleaned_data.get('blocked_from') or today) < today:
            self.add_error('blocked_from', _("Preferably select a date in the future."))
        if (cleaned_data.get('blocked_until') or today) < today:
            self.add_error('blocked_until', _("Preferably select a date in the future."))

        if cleaned_data.get('blocked_until') and self.instance.blocked_from:
            if cleaned_data['blocked_until'] <= self.instance.blocked_from:
                raise forms.ValidationError(_("Unavailability should finish after it starts."))
        if cleaned_data.get('blocked_from') and self.instance.blocked_until:
            if cleaned_data['blocked_from'] >= self.instance.blocked_until:
                raise forms.ValidationError(_("Unavailability should start before it finishes."))

        return cleaned_data


@client_side_validated
class PhoneForm(forms.ModelForm):
    class Meta:
        model = Phone
        fields = ['number', 'type', 'country', 'comments']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'profile'):
            self.profile = self.instance.profile
        self.fields['number'].widget.input_type = 'tel'

    def clean(self):
        """Checks if the number and the profile are unique together."""
        cleaned_data = super().clean()
        if 'number' in cleaned_data:
            data = cleaned_data['number'].as_e164
            phones = Phone.objects.filter(number=data, profile=self.profile)
            number_list = phones.values_list('number', flat=True)
            if data in number_list:
                # Check is done for object creation and for object update.
                if not self.instance.number or data != self.instance.number.as_e164:
                    self.add_error('number', _("You already have this telephone number."))
        return cleaned_data


class PhoneCreateForm(PhoneForm):
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        phone = super().save(commit=False)
        phone.profile = self.profile
        if commit:
            phone.save()
        return phone
    save.alters_data = True


class UserAuthorizeForm(forms.Form):
    user = forms.CharField(label=_("Authorize user"), max_length=254)
    remove = forms.BooleanField(required=False, initial=False, widget=forms.widgets.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].widget.attrs['placeholder'] = _("username")
        self.fields['user'].widget.attrs['inputmode'] = 'verbatim'

    def clean(self):
        cleaned_data = super().clean()
        if 'user' not in cleaned_data:
            return
        user_qualifier = cleaned_data['user']
        if not cleaned_data.get('remove', False):
            try:
                User.objects.get(username=user_qualifier).profile
            except User.DoesNotExist:
                raise forms.ValidationError(_("User does not exist"))
            except Profile.DoesNotExist:
                raise forms.ValidationError(_("User has not set up a profile"))
        return cleaned_data


class UserAuthorizedOnceForm(UserAuthorizeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].widget = forms.widgets.HiddenInput()
        self.fields['remove'].initial = True


@client_side_validated
class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['title', 'first_name', 'last_name', 'names_inversed', 'birth_date']
        error_messages = {
            'birth_date': {'max_value': _("A family member cannot be future-born (even if planned).")},
        }

    def __init__(self, *args, **kwargs):
        self.place = kwargs.pop('place')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['inputmode'] = 'latin-name'
        self.fields['last_name'].widget.attrs['inputmode'] = 'latin-name'
        if not self.place_has_family_members():
            self.fields['first_name'].help_text = _(
                "Leave empty if you only want to indicate that other people are present in the house.")
        self.fields['birth_date'].widget.attrs['pattern'] = (
            '[1-2][0-9]{3}-((0[1-9])|(1[0-2]))-((0[1-9])|([12][0-9])|(3[0-1]))')
        self.fields['birth_date'].widget.attrs['data-date-end-date'] = '0d'
        self.fields['birth_date'].widget.attrs['placeholder'] = 'jjjj-mm-tt'

    def place_has_family_members(self):
        return len(self.place.family_members_cache()) != 0 and not self.place.family_is_anonymous

    def clean(self):
        """Verifies that first name and last name convey some information together."""
        cleaned_data = super().clean()
        if 'first_name' in cleaned_data and 'last_name' in cleaned_data and self.place_has_family_members():
            if not "".join([cleaned_data['first_name'], cleaned_data['last_name']]):
                raise forms.ValidationError(_("The name cannot be empty, "
                                              "at least first name or last name are required."))
        return cleaned_data


class FamilyMemberCreateForm(FamilyMemberForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self):
        family_member = super().save()
        self.place.family_members.add(family_member)
        return family_member
    save.alters_data = True
