from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import (
    BinaryField, BooleanField, Case, CharField, Q, Value, When,
)
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _

from django_countries.data import COUNTRIES

from core.models import SiteConfiguration
from maps.widgets import MapboxGlWidget

from .models import (
    Phone, Place, Profile, VisibilitySettings,
    VisibilitySettingsForFamilyMembers, VisibilitySettingsForPhone,
    VisibilitySettingsForPlace, VisibilitySettingsForPublicEmail,
)
from .utils import geocode, value_without_invalid_marker
from .validators import TooNearPastValidator, client_side_validated
from .widgets import ClearableWithPreviewImageInput

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

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save(update_fields=['email', 'modified'])
        return profile


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
        }


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


class VisibilityForm(forms.ModelForm):
    class Meta:
        model = VisibilitySettings
        fields = [
            'visible_online_public',
            'visible_online_authed',
            'visible_in_book',
        ]
    # The textual note (for assistive technologies), placed before the data.
    hint = forms.CharField(required=False, disabled=True)
    # Whether to nudge the data to the right, creating a second level.
    indent = forms.BooleanField(required=False, disabled=True)

    def __init__(self, *args, **kwargs):
        self.requested_pk = kwargs.pop('request_pk', None)
        self.profile = kwargs.pop('request_profile', None)
        read_only = kwargs.pop('read_only', False)
        super().__init__(*args, **kwargs)
        if read_only:
            for f in self.fields:
                self.fields[f].disabled = True

        widget_settings = {
            'data-toggle': 'toggle',
            'data-on': _("Yes"),
            'data-off': _("No"),
            'data-size': 'mini',
            'data-on-ajax-setup': 'updateVisibilitySetup',
            'data-on-ajax-success': 'updateVisibilityResult',
            'data-on-ajax-error': 'updateVisibilityFailure',
            # autocomplete attribute is required for Firefox to drop
            # caching and refresh the checkbox on each page reload.
            'autocomplete': 'off',
        }
        widget_classes = ' ajax-on-change'

        for venue in self.venues():
            attrs = venue.field.widget.attrs
            attrs.update(widget_settings)
            attrs['class'] = attrs.get('class', '') + widget_classes
            if venue.venue_name == 'in_book' and not self.obj.visibility.printable:
                venue.field.disabled = True
                venue.field.initial = False
                self.initial[venue.field_name] = False
                if isinstance(self.obj, Place):
                    venue.hosting_notification = True
            elif not read_only:
                venue.field.disabled = not self.obj.visibility.rules[venue.venue_name]
            if venue.venue_name.startswith('online_'):
                attrs.update({'data-tied': str(self.obj.visibility.rules.get('tied_online', False))})

    def venues(self, restrict_to=''):
        """
        Generator of bound fields corresponding to the visibility venues:
        online_public, online_authed, and in_book. Each bound field is updated
        to include the name of the venue.
        """
        for f in self.fields:
            if f.startswith(self._meta.model._PREFIX+restrict_to):
                bound_field = self[f]
                bound_field.field_name, bound_field.venue_name = f, f[len(self._meta.model._PREFIX):]
                yield bound_field

    @cached_property
    def obj(self):
        """
        Returns the object itself or a wrapper (in the case of a field), for
        simplified and unified access to the visibility object in templates.
        """
        if self.is_bound and self.instance.model_type == self.instance.DEFAULT_TYPE:
            raise ValueError("Form is bound but no visibility settings object was provided, "
                             "for key {pk} and {profile!r}. This most likely indicates tampering."
                             .format(pk=self.requested_pk, profile=self.profile))
        wrappers = {
            VisibilitySettingsForFamilyMembers.type(): self.FamilyMemberAsset,
            VisibilitySettingsForPublicEmail.type(): self.EmailAsset,
        }
        return wrappers.get(self.instance.model_type, lambda c: c)(self.instance.content_object)

    class FamilyMemberAsset:
        """
        Wrapper for the `family_members` field of a Place.
        """
        def __init__(self, for_place):
            self.title = for_place._meta.get_field('family_members').verbose_name
            self.visibility = for_place.family_members_visibility

        @property
        def icon(self):
            template = ('<span class="fa ps-users" title="{title}" '
                        '      data-toggle="tooltip" data-placement="left"></span>')
            return format_html(template, title=_("family members").capitalize())

        def __str__(self):
            return str(self.title)

    class EmailAsset:
        """
        Wrapper for the `email` field of a Profile.
        """
        def __init__(self, for_profile):
            self.data = for_profile.email
            self.visibility = for_profile.email_visibility

        @property
        def icon(self):
            template = ('<span class="fa fa-envelope" title="{title}" '
                        '      data-toggle="tooltip" data-placement="bottom"></span>')
            return format_html(template, title=_("public email").capitalize())

        def __str__(self):
            return value_without_invalid_marker(self.data)

    def clean_visible_in_book(self):
        """
        The in_book venue is manipulated manually in form init, so that the
        checkbox appears as "off" when place is not offered for accommodation,
        independently of its actual value.
        The clean method ensures that the value is restored to the actual one;
        otherwise the database will be updated with the "off" value.
        """
        venue = next(self.venues('in_book'))
        if venue.field.disabled:
            return self.obj.visibility[venue.venue_name]
        else:
            return self.cleaned_data['visible_in_book']

    def save(self, commit=True):
        """
        Adds a bit of magic to the saving of the visibility object.
        When data is made visible in public, it will automatically become
        visible also to the authorized users. And when it is made hidden for
        authorized users, it will automatically become hidden for public.
        """
        visibility = super().save(commit=False).as_specific()
        venue, field_name = None, ''
        for field in self.venues('online'):
            if field.field_name in self.changed_data:
                venue, field_name = field.venue_name, field.field_name
        value = self.cleaned_data.get(field_name)
        counterparty = {
            'online_public': 'online_authed', 'online_authed': 'online_public', None: '',
        }[venue]
        ripple = [
            (value) and venue == 'online_public',
            (not value) and venue == 'online_authed',
            (not value) and venue == 'online_public' and visibility.rules.get('tied_online'),
        ]
        if any(ripple):
            visibility[counterparty] = value
        if commit:
            visibility.save(update_fields=[v.field_name for v in self.venues()])
        return visibility


class VisibilityFormSetBase(forms.BaseModelFormSet):
    """
    Provides a unified basis for a FormSet of the visibility models, linked to
    a specific profile. The linkage is to all relevant objects, such as places
    and phones, and to fields with selective display-ability.
    """
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        self.modified_venue = kwargs.pop('dirty', None)
        super().__init__(*args, **kwargs)

        PLACE, FAMILY_MEMBERS, PHONE, PUBLIC_EMAIL = (vis.type() for vis in [
            VisibilitySettingsForPlace, VisibilitySettingsForFamilyMembers,
            VisibilitySettingsForPhone, VisibilitySettingsForPublicEmail,
        ])
        # Gathering all data items linked to the profile.
        what = Q()
        owned_places = self.profile.owned_places.exclude(deleted=True).prefetch_related('family_members')
        what |= Q(model_type=PLACE, place__in=owned_places)
        what |= Q(model_type=FAMILY_MEMBERS, family_members__in=[
            place.pk for place in owned_places
            if len(place.family_members_cache()) != 0 and not place.family_is_anonymous
        ])
        what |= Q(model_type=PHONE, phone__in=self.profile.phones.exclude(deleted=True))
        what |= Q(model_type=PUBLIC_EMAIL, profile=self.profile) if self.profile.email else Q()
        qs = VisibilitySettings.objects.filter(what)
        # Forcing a specific sort order: places (with their corresponding family members),
        # then phones, then a public email if present.
        qs = qs.annotate(
            level_primary=Case(
                When(Q(model_type=PLACE) | Q(model_type=FAMILY_MEMBERS), then=1),
                When(model_type=PHONE, then=2),
                When(model_type=PUBLIC_EMAIL, then=3),
                default=9,
                output_field=BinaryField(),
            ),
            level_secondary=Case(
                When(model_type=PLACE, then=10),
                When(model_type=FAMILY_MEMBERS, then=11),
                output_field=BinaryField(),
            ),
        )
        # Preparing presentation settings.
        qs = qs.annotate(
            hint=Case(
                When(model_type=PLACE, then=Value(str(_("A place in")))),
                When(model_type=PHONE, then=Value(str(_("Phone number")))),
                When(model_type=PUBLIC_EMAIL, then=Value(str(_("Email address")))),
                output_field=CharField(),
            ),
            indent=Case(
                When(model_type=FAMILY_MEMBERS, then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )
        self.queryset = qs.order_by('level_primary', 'model_id', 'level_secondary')

    def get_form_kwargs(self, index):
        """
        Forwards to the individual forms certain request parameters, which are
        available here but normally not for the forms themselves.
        """
        if index >= len(self.queryset):
            raise IndexError("Form #{id} does not exist in the queryset, for {profile!r}. "
                             "This most likely indicates tampering."
                             .format(id=index, profile=self.profile))
        kwargs = super().get_form_kwargs(index)
        kwargs['initial'] = {
            field: getattr(self.queryset[index], field) for field in ['hint', 'indent']
        }
        if self.is_bound:
            pk_key = "{form_prefix}-{pk_field}".format(
                form_prefix=self.add_prefix(index), pk_field=self.model._meta.pk.name)
            kwargs['request_pk'] = self.data.get(pk_key)
            kwargs['request_profile'] = self.profile
        return kwargs
