from django import forms
from django.db.models import (
    BinaryField, BooleanField, Case, CharField, Q, Value, When,
)
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ..models import (
    Place, VisibilitySettings, VisibilitySettingsForFamilyMembers,
    VisibilitySettingsForPhone, VisibilitySettingsForPlace,
    VisibilitySettingsForPublicEmail,
)
from ..utils import value_without_invalid_marker


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
            'data-on-ajax-error': 'updatePrivacyFailure',
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

    save.alters_data = True


class VisibilityFormSetBase(forms.BaseModelFormSet):
    """
    Provides a unified basis for a FormSet of the visibility models, linked to
    a specific profile. The linkage is to all relevant objects, such as places
    and phones, and to fields with selective display-ability.
    """

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        self.read_only = kwargs.pop('read_only', False)
        self.modified_venue = kwargs.pop('dirty', None)
        super().__init__(
            *args,
            error_messages={
                'missing_management_form':
                    _("Form management data is missing or has been tampered with."),
            },
            **kwargs)

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
                default=Value(""),
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
        kwargs['read_only'] = self.read_only
        if self.is_bound:
            pk_key = "{form_prefix}-{pk_field}".format(
                form_prefix=self.add_prefix(index), pk_field=self.model._meta.pk.name)
            kwargs['request_pk'] = self.data.get(pk_key)
            kwargs['request_profile'] = self.profile
        return kwargs
