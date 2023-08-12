import logging
import re
from collections import namedtuple
from datetime import date
from itertools import groupby

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from django.db.models import Case, When
from django.db.models.fields import BLANK_CHOICE_DASH
from django.utils.functional import keep_lazy_text, lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from crispy_forms.bootstrap import PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field
from django_countries.fields import Country

from core.auth import AuthRole
from core.models import SiteConfiguration
from core.utils import join_lazy, mark_safe_lazy, sort_by
from hosting.widgets import FormDivider
from maps import SRID
from maps.widgets import MapboxGlWidget

from ..countries import (
    COUNTRIES_DATA, SUBREGION_TYPES, countries_with_mandatory_region,
)
from ..models import (
    Condition, CountryRegion, LocationConfidence,
    LocationType, Place, Profile, Whereabouts,
)
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
        error_messages = {
            'conditions': {
                'invalid_pk_value': _("“%(pk)s” is not a valid value."),
            },
        }

    class _validation_meta:
        meeting_required_fields = ['city', ]
        hosting_required_fields = ['address', 'city', 'closest_city', ]
        book_required_fields = [
            'address', 'city', 'closest_city', 'available',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        subregion_form = SubregionForm(
            self._meta.model, 'state_province',
            for_country=self.data.get('country') or self.instance.country,
            operation=f"editing place #{self.instance.pk}" if self.instance.id else "adding new place",
        )
        self.fields['state_province'] = subregion_form.fields['state_province']
        self.country_regions = getattr(subregion_form, 'country_regions', None)

        self.helper = FormHelper(self)
        self.fields['state_province'].widget.attrs['autocomplete'] = 'region'
        # Combine the postcode and the city fields together in one line.
        postcode_field_index = self.helper.layout.fields.index('postcode')
        self.helper[postcode_field_index:postcode_field_index+2].wrap_together(Div, css_class='row')
        self.helper['postcode'].wrap(Field, wrapper_class='col-xxs-12 col-xs-4')
        self.helper['city'].wrap(Field, wrapper_class='col-xxs-12 col-xs-8')
        self.fields['postcode'].widget.attrs['autocomplete'] = 'postal-code'
        self.fields['city'].widget.attrs['autocomplete'] = 'locality'
        # Bigger input area for the address by default.
        self.fields['address'].widget.attrs['rows'] = 2
        self.fields['address'].widget.attrs['autocomplete'] = 'street-address'
        # Split address details from the description and conditions.
        self.helper.layout.insert(self.helper.layout.fields.index('max_guest'), FormDivider())
        # Combine the count fields together in one line.
        max_guests_field_index = self.helper.layout.fields.index('max_guest')
        self.helper[max_guests_field_index:max_guests_field_index+3].wrap_together(Div, css_class='row')
        for field, field_icon in {'max_guest': 'fa-street-view', 'max_night': 'fa-regular fa-moon'}.items():
            self.helper[field].wrap(
                PrependedText,
                f'<span class="fa {field_icon}"></span>',
                wrapper_class='col-xxs-12 col-xs-6 col-sm-4',
                css_class='text-center')
        self.helper['contact_before'].wrap(Field, wrapper_class='col-xs-12 col-sm-4', css_class='text-center')
        # Placeholder for the multiple-select field of conditions.
        self.fields['conditions'].widget.attrs['data-placeholder'] = _("Choose your conditions...")
        # Grouping and sorting of condition options.
        conditions_queryset = (
            Condition.objects
            .annotate(
                category_group=Case(
                    When(category=Condition.Categories.SLEEPING_CONDITIONS, then=1),
                    When(category=Condition.Categories.IN_THE_HOUSE, then=2),
                    When(category=Condition.Categories.ON_THE_OUTSIDE, then=3),
                    default=4),
            )
            .order_by('category_group', 'category', Condition.active_name_field())
        )
        conditions_iterator = self.fields['conditions'].iterator(self.fields['conditions'])
        self.fields['conditions'].choices = [
            (
                condition_group,
                [conditions_iterator.choice(cond) for cond in conditions]
            )
            for condition_group, conditions
            in groupby(conditions_queryset, key=lambda cond: cond.get_category_display())
        ]

    def clean_state_province(self):
        state_province, country = self.cleaned_data['state_province'], self.cleaned_data.get('country')
        if not country:
            return state_province

        if country in countries_with_mandatory_region() and not state_province:
            # Verifies that the region is indeed indicated when it is mandatory.
            if hasattr(self.fields['state_province'], 'localised_label'):
                message = _("For an address in {country}, the name of the "
                            "{region_type} must be indicated.")
            else:
                message = _("For an address in {country}, the name of the "
                            "state or province must be indicated.")
            raise forms.ValidationError(
                format_lazy(
                    message,
                    country=(
                        lazy(lambda country_obj: country_obj.name.split(' (')[0], str)(Country(country))
                    ),
                    region_type=(
                        keep_lazy_text(lambda label: label.lower())(self.fields['state_province'].label)
                    ),
                )
            )
        return state_province

    def clean_postcode(self):
        postcode, country = self.cleaned_data['postcode'], self.cleaned_data.get('country')
        if not country or not postcode:
            return postcode

        postcode_re = COUNTRIES_DATA[country]['postcode_regex']
        if postcode_re and COUNTRIES_DATA[country].get('postal_code_prefix'):
            prefix_re = re.escape(COUNTRIES_DATA[country]['postal_code_prefix'])
            postcode_re = r'(?:{})?'.format(prefix_re) + postcode_re

        if postcode_re and not re.fullmatch(postcode_re, postcode.upper()):
            accepted_patterns = COUNTRIES_DATA[country]['postcode_format'].split('|')
            raise forms.ValidationError(mark_safe_lazy(
                format_lazy(
                    _("Postal code should follow the pattern {} (# is digit, @ is a letter)."),
                    join_lazy(_(" or "), list(map(lambda pn: f"<kbd>{pn}</kbd>", accepted_patterns)))
                )
            ))
        # Removing non-alphanumeric characters (except for the allowed separators 'space'
        # and 'dash'), is mainly for freeform postal codes in countries for which no regex
        # is defined.
        return re.sub(r'[^A-Z0-9 -]', '', ' '.join(postcode.split()).upper(), re.ASCII)

    def clean(self):
        cleaned_data = super().clean()
        config = SiteConfiguration.get_solo()

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
                    message += [cond.form_error]
        if message:
            raise forms.ValidationError(message)

        return cleaned_data

    def _format_address(self, with_street=True):
        address = {
            'street': self.cleaned_data['address'].replace('\r\n', ', ') if with_street else '',
            'zip': self.cleaned_data['postcode'].replace(' ', ''),
            'city': self.cleaned_data['city'],
            'state': getattr(self.cleaned_region, 'latin_code', '') or self.cleaned_data['state_province'],
        }
        return '{street}, {zip} {city}, {state}'.format(**address).lstrip(', ')

    def _geocode_new_city(self):
        geocities = Whereabouts.objects.filter(
            type=LocationType.CITY,
            name=self.cleaned_data['city'].upper(),
            country=self.cleaned_data['country'],
        )
        if self.cleaned_data['country'] in countries_with_mandatory_region():
            region = self.cleaned_data['state_province'].upper()
            geocities = geocities.filter(state=region)
        else:
            region = ''
        if not geocities.exists():
            city_location = geocode_city(
                self.cleaned_data['city'],
                state_province=(
                    getattr(self.cleaned_region, 'latin_code', '')
                    or self.cleaned_data['state_province']
                ),
                country=self.cleaned_data['country'],
            )
            if city_location:
                Whereabouts.objects.create(
                    type=LocationType.CITY,
                    name=self.cleaned_data['city'].upper(),
                    state=region,
                    country=self.cleaned_data['country'],
                    bbox=LineString(
                        city_location.bbox['southwest'], city_location.bbox['northeast'],
                        srid=SRID,
                    ),
                    center=Point(city_location.xy, srid=SRID),
                )

    def save(self, commit=True):
        place = super().save(commit=False)

        residence_change = ['country', 'state_province', 'city', 'postcode']
        if any(field in self.changed_data and field in self.cleaned_data for field in residence_change):
            # When the user moves to a different country, state, or city their
            # previously saved location (geopoint) is not up-to-date anymore.
            place.location = None

        if place.location is None or place.location.empty:
            # Only recalculate the location if it was not already geocoded before.
            try:
                # `country_regions` will always be a valid QuerySet here, because `country`
                # is a required field, validated before save() can be called.
                self.cleaned_region = self.country_regions.get(iso_code=self.cleaned_data['state_province'])
            except CountryRegion.DoesNotExist:
                self.cleaned_region = None
            location = geocode(self._format_address(), country=self.cleaned_data['country'], private=True)
            if location and not location.point and 'address' in self.changed_data:
                # Try again without the address block when location cannot be determined.
                # This is because users often put stuff into the address block, which the
                # poor geocoder has trouble deciphering.
                location = geocode(
                    self._format_address(with_street=False),
                    country=self.cleaned_data['country'], private=True)
            if location and location.point and location.confidence > LocationConfidence.GT_25KM:
                # https://geocoder.opencagedata.com/api#confidence
                place.location = location.point
            place.location_confidence = (
                (getattr(location, 'confidence', None) or LocationConfidence.UNDETERMINED)
                if place.location
                else LocationConfidence.UNDETERMINED
            )

            if self.cleaned_data['city'] != '':
                # Create a new geocoding of the user's city if we don't have it in the database yet.
                self._geocode_new_city()

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


class SubregionForm(forms.Form):
    def __init__(self, model, field, *args, for_country=None, operation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.fields = forms.fields_for_model(model, [field])

        if for_country and for_country in COUNTRIES_DATA:
            country_data = COUNTRIES_DATA[for_country]
            self.country_regions = CountryRegion.objects.filter(country=for_country)
            regions = [
                (r.iso_code, r.get_display_value_with_esperanto())
                for r in self.country_regions
            ] + BLANK_CHOICE_DASH
            if len(regions) > 1:
                # Replacing a form field must happen before the `_bound_fields_cache` is populated.
                # Note: the 'chosen' JS addon interferes with normal HTML form functioning (including
                #       showing form validation errors), that is why we keep the field not required.
                # Using a ModelChoiceField here, while more natural, is also more cumbersome, since
                # both the field itself (for labels) and the ModelChoiceIterator (for sorting) must
                # be subclassed.
                RegionChoice = namedtuple('Choice', 'code, label')
                self.fields[field] = forms.ChoiceField(
                    choices=sort_by(['label'], (RegionChoice(*r) for r in regions)),
                    initial=self.fields[field].initial,
                    required=False,
                    label=self.fields[field].label,
                    help_text=self.fields[field].help_text,
                    error_messages={
                        'invalid_choice': _(
                            "Choose from the list. The name provided by you is not known."
                        ),
                    },
                )
            elif for_country in countries_with_mandatory_region():
                # We don't want to raise an error, preventing the user from using the form,
                # but we do want to log it and notify the administrators.
                logging.getLogger('PasportaServo.address').error(
                    "Service misconfigured: Mandatory regions for %s are not defined!"
                    "  (noted when %s)",
                    getattr(for_country, 'code', for_country),
                    operation or "preparing choice field",
                )
            region_type = country_data.get('administrative_area_type')
            if region_type in SUBREGION_TYPES:
                capitalize_lazy = keep_lazy_text(lambda label: label.capitalize())
                self.fields[field].label = capitalize_lazy(SUBREGION_TYPES[region_type])
                self.fields[field].localised_label = True

        self.fields[field].widget.attrs['data-search-threshold'] = 6


class PlaceLocationForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['location']
        widgets = {
            'location': MapboxGlWidget(),
        }

    def __init__(self, *args, **kwargs):
        self.view_role = kwargs.pop('view_role')
        super().__init__(*args, **kwargs)
        self.fields['location'].widget.attrs['data-selectable-zoom'] = 11.5

    def save(self, commit=True):
        place = super().save(commit=False)
        if self.cleaned_data.get('location'):
            if self.view_role >= AuthRole.SUPERVISOR:
                place.location_confidence = LocationConfidence.CONFIRMED
            else:
                place.location_confidence = LocationConfidence.EXACT
        else:
            place.location_confidence = LocationConfidence.UNDETERMINED
        if commit:
            place.save(update_fields=['location', 'location_confidence'])
        return place
    save.alters_data = True


class PlaceBlockForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['blocked_from', 'blocked_until']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget_settings = {
            'data-date-start-date': '-0d',
            'data-date-force-parse': 'false',
            'data-date-autoclose': 'true',
            'placeholder': 'jjjj-mm-tt',
        }

        for field_name in self._meta.fields:
            self.fields[field_name].widget.attrs.update(widget_settings)

    def filter_cleaned_data(self, cleaned_data):
        return cleaned_data

    def clean(self):
        """
        Checks that place was not deleted (in this case, update is not allowed).
        Checks if starting date is earlier than the ending date.
        """
        if self.instance.deleted_on:
            raise forms.ValidationError(_("Deleted place"), code='deleted')

        cleaned_data = super().clean()
        cleaned_data = self.filter_cleaned_data(cleaned_data)
        CleanedData = namedtuple('CleanedData', 'blocked_from, blocked_until')
        data = CleanedData(cleaned_data.get('blocked_from'), cleaned_data.get('blocked_until'))

        today = date.today()
        if (data.blocked_from or today) < today:
            self.add_error('blocked_from', _("Preferably select a date in the future."))
        if (data.blocked_until or today) < today:
            self.add_error('blocked_until', _("Preferably select a date in the future."))

        if self.__class__ is PlaceBlockForm:
            compare_with = data
        if self.__class__ is PlaceBlockQuickForm:
            compare_with = self.instance

        if data.blocked_until and compare_with.blocked_from:
            if data.blocked_until <= compare_with.blocked_from:
                raise forms.ValidationError(_("Unavailability should finish after it starts."),
                                            code='dates_agreement')
        if data.blocked_from and compare_with.blocked_until:
            if data.blocked_from >= compare_with.blocked_until:
                raise forms.ValidationError(_("Unavailability should start before it finishes."),
                                            code='dates_agreememt')

        return cleaned_data


class PlaceBlockQuickForm(PlaceBlockForm):
    dirty = forms.ChoiceField(
        choices=(('blocked_from', 1), ('blocked_until', 2)),
        widget=forms.HiddenInput, label="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget_settings = {
            'data-on-ajax-setup': 'blockPlaceSetup',
            'data-on-ajax-success': 'blockPlaceSuccess',
        }
        widget_classes = ' form-control quick-form-control input-sm ajax-on-change'

        for (field_name, field_label) in (('blocked_from', _("commencing on")),
                                          ('blocked_until', _("concluding on"))):
            field = self.fields[field_name]
            field.label = field_label
            attrs = field.widget.attrs
            attrs.update(widget_settings)
            attrs['class'] = attrs.get('class', '') + widget_classes
            value = self[field_name].value()
            attrs['data-value'] = field.widget.format_value(value) if value is not None else ''

    def filter_cleaned_data(self, cleaned_data):
        # Only inspect the field that was just changed (named in the 'dirty' parameter).
        cleaned_data = dict((k, v) for k, v in cleaned_data.items()
                            if k == cleaned_data.get('dirty', ''))
        return cleaned_data


class UserAuthorizeForm(forms.Form):
    user = forms.CharField(
        label=_("Authorize user"),
        max_length=254)
    remove = forms.BooleanField(
        required=False, initial=False,
        widget=forms.widgets.HiddenInput)

    def __init__(self, *args, **kwargs):
        unauthorize = kwargs.pop('unauthorize', False)
        super().__init__(*args, **kwargs)
        if unauthorize:
            self.fields['user'].widget = forms.widgets.HiddenInput()
            self.fields['remove'].initial = True
        else:
            self.fields['user'].widget.attrs['placeholder'] = _("username")
            self.fields['user'].widget.attrs['inputmode'] = 'verbatim'
        self.helper = FormHelper(self)
        # The form errors should be rendered in smaller box and font.
        self.helper.form_error_class = 'alert-small'

    def clean(self):
        cleaned_data = super().clean()
        if 'user' not in cleaned_data:
            return
        user_qualifier = cleaned_data['user']
        if not cleaned_data.get('remove', False):
            try:
                user_id = User.objects.values_list('pk', flat=True).get(username=user_qualifier)
                Profile.all_objects.values('pk').get(user=user_id)
            except User.DoesNotExist:
                raise forms.ValidationError(_("User does not exist"))
            except Profile.DoesNotExist:
                raise forms.ValidationError(_("User has not set up a profile"))
        return cleaned_data
