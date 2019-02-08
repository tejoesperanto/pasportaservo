from collections import namedtuple
from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _

from django_countries.fields import Country

from core.models import SiteConfiguration
from maps import COUNTRIES_WITH_MANDATORY_REGION, SRID
from maps.widgets import MapboxGlWidget

from ..models import LOCATION_CITY, Place, Profile, Whereabouts
from ..utils import geocode, geocode_city
from ..validators import TooNearPastValidator

User = get_user_model()


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
        meeting_required_fields = ['city', ]
        hosting_required_fields = ['address', 'city', 'closest_city', ]
        book_required_fields = [
            'address', 'city', 'closest_city', 'available',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].widget.attrs['rows'] = 2
        self.fields['conditions'].help_text = ""
        self.fields['conditions'].widget.attrs['data-placeholder'] = _("Choose your conditions...")

    def clean(self):
        cleaned_data = super().clean()
        config = SiteConfiguration.get_solo()

        if cleaned_data.get('country') in COUNTRIES_WITH_MANDATORY_REGION and not cleaned_data.get('state_province'):
            # Verifies that the region is indeed indicated when it is mandatory.
            message = _("For an address in {country}, the name of the state or province must be indicated.")
            self.add_error('state_province', format_lazy(message, country=Country(cleaned_data['country']).name))

        for_hosting = cleaned_data['available']
        for_meeting = cleaned_data['tour_guide'] or cleaned_data['have_a_drink']
        if any([for_hosting, for_meeting]):
            # Verifies that user is of correct age if they want to host or meet visitors.
            profile = self.profile if hasattr(self, 'profile') else self.instance.owner
            try:
                allowed_age = config.host_min_age if for_hosting else config.meet_min_age
                TooNearPastValidator(allowed_age)(profile.birth_date or date.today())
            except forms.ValidationError:
                if for_hosting:
                    self.add_error('available', "")
                    message = _("The minimum age to be allowed hosting is {age:d}.")
                else:
                    if cleaned_data['tour_guide']:
                        self.add_error('tour_guide', "")
                    if cleaned_data['have_a_drink']:
                        self.add_error('have_a_drink', "")
                    message = _("The minimum age to be allowed meeting with visitors is {age:d}.")
                raise forms.ValidationError(format_lazy(message, age=allowed_age))

        # Some fields are required if user wants to host or to meet visitors,
        # or wants their data to be printed in the book.
        Req = namedtuple('Requirements', 'on, required_fields, form_error, field_error')
        requirements = [
            Req(for_hosting, self._validation_meta.hosting_required_fields,
                None,
                forms.ValidationError(_("This field is required if you accept guests."),
                                      code='host_condition')),
            Req(for_meeting, self._validation_meta.meeting_required_fields,
                None,
                forms.ValidationError(_("This field is required if you meet visitors."),
                                      code='host_condition')),
            Req(cleaned_data['in_book'], self._validation_meta.book_required_fields,
                _("You want to be in the printed edition of Pasporta Servo. "
                  "In order to have a quality product, some fields are required. "
                  "If you think there is a problem, please contact us."),
                forms.ValidationError(_("This field is required to be printed in the book."),
                                      code='book_condition')),
        ]
        message = []

        for cond in requirements:
            all_filled = all([cleaned_data.get(field, False) for field in cond.required_fields])
            if cond.on and not all_filled:
                for field in cond.required_fields:
                    if not cleaned_data.get(field, False) and not self.has_error(field, cond.field_error.code):
                        self.add_error(field, cond.field_error)
                if cond.form_error:
                    message += forms.ValidationError(cond.form_error)
        if message:
            raise forms.ValidationError(message)

        return cleaned_data

    def format_address(self, with_street=True):
        address = {
            'street': self.cleaned_data.get('address').replace('\r\n', ',') if with_street else '',
            'zip': self.cleaned_data.get('postcode').replace(' ', ''),
            'city': self.cleaned_data.get('city'),
            'state': self.cleaned_data.get('state_province'),
        }
        return '{street}, {zip} {city}, {state}'.format(**address).lstrip(', ')

    def save(self, commit=True):
        place = super().save(commit=False)

        residence_change = ['country', 'state_province', 'city', 'postcode']
        if hasattr(self, 'instance') and \
                any(field in self.changed_data and field in self.cleaned_data for field in residence_change):
            # When the user moves to a different country, state, or city their
            # previously saved location (geopoint) is not up-to-date anymore.
            place.location = None

        if place.location is None or place.location.empty:
            # Only recalculate the location if it was not already geocoded before.
            location = geocode(self.format_address(), country=self.cleaned_data['country'], private=True)
            if location and not location.point and 'address' in self.changed_data:
                # Try again without the address block when location cannot be determined.
                # This is because users often put stuff into the address block, which the
                # poor geocoder has trouble deciphering.
                location = geocode(
                    self.format_address(with_street=False),
                    country=self.cleaned_data['country'], private=True)
            if location and location.point and location.confidence > 1:
                # https://geocoder.opencagedata.com/api#confidence
                place.location = location.point
            place.location_confidence = getattr(location, 'confidence', None) or 0

            # Create a new geocoding of the user's city if we don't have it in the database yet.
            geocities = Whereabouts.objects.filter(
                type=LOCATION_CITY, name=self.cleaned_data['city'].upper(), country=self.cleaned_data['country'])
            if self.cleaned_data['country'] in COUNTRIES_WITH_MANDATORY_REGION:
                region = self.cleaned_data['state_province'].upper()
                geocities = geocities.filter(state=region)
            else:
                region = ''
            if not geocities.exists():
                city_location = geocode_city(
                    self.cleaned_data['city'],
                    state_province=self.cleaned_data['state_province'],
                    country=self.cleaned_data['country'])
                if city_location:
                    Whereabouts.objects.create(
                        type=LOCATION_CITY,
                        name=self.cleaned_data['city'].upper(),
                        state=region,
                        country=self.cleaned_data['country'],
                        bbox=LineString(city_location.bbox['southwest'], city_location.bbox['northeast'], srid=SRID),
                        center=Point(city_location.xy, srid=SRID),
                    )

        if commit:
            place.save()
            self.save_m2m()
        self.confidence = place.location_confidence
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
            self.save_m2m()
        return place
    save.alters_data = True


class PlaceLocationForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['location']
        widgets = {
            'location': MapboxGlWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].widget.attrs['data-selectable-zoom'] = 11.5

    def save(self, commit=True):
        place = super().save(commit=False)
        if self.cleaned_data.get('location'):
            place.location_confidence = 100
        else:
            place.location_confidence = 0
        if commit:
            place.save(update_fields=['location', 'location_confidence'])
        return place


class PlaceBlockForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['blocked_from', 'blocked_until']
    dirty = forms.ChoiceField(
        choices=(('blocked_from', 1), ('blocked_until', 2)),
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
        """
        Checks if starting date is earlier than the ending date.
        """
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


class UserAuthorizeForm(forms.Form):
    user = forms.CharField(
        label=_("Authorize user"),
        max_length=254)
    remove = forms.BooleanField(
        required=False, initial=False,
        widget=forms.widgets.HiddenInput)

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
