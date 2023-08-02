import re
from collections import namedtuple
from datetime import date
from enum import Enum, IntEnum
from functools import partial, partialmethod

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models import LineStringField, PointField
from django.db import models, transaction
from django.db.models import F, Q, Value as V
from django.db.models.functions import Concat, Substr
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import classonlymethod
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy
from django.utils.translation import (
    get_language, gettext_lazy as _,
    override as override_translation, pgettext_lazy,
)

from commonmark import commonmark
from django_countries.fields import CountryField
from django_extensions.db.models import TimeStampedModel
from simplemde.fields import SimpleMDEField
from slugify import Slugify
from unidecode import unidecode

from core.utils import camel_case_split
from maps import SRID

from .countries import COUNTRIES_DATA
from .fields import (
    PhoneNumberField, RangeIntegerField, StyledEmailField, SuggestiveField,
)
from .filters.places import (
    HostingFilter, InBookFilter, MeetingFilter,
    OkForBookFilter, OkForGuestsFilter,
)
from .gravatar import email_to_gravatar
from .managers import (
    ActiveStatusManager, AvailableManager, NotDeletedManager,
    NotDeletedRawManager, TrackingManager,
)
from .utils import RenameAndPrefixAvatar, value_without_invalid_marker
from .validators import (
    TooFarPastValidator, validate_image, validate_latin,
    validate_no_digit, validate_not_all_caps, validate_not_in_future,
    validate_not_too_many_caps, validate_size,
)


class LocationType(Enum):
    CITY = 'C'
    REGION = 'R'
    UNKNOWN = 'U'

    def __str__(member):
        return member.value


class LocationConfidence(IntEnum):
    # https://opencagedata.com/api#confidence
    UNDETERMINED = 0    # Geocoder was unable to determine a position or bounding box.
    GT_25KM = 1         # 25 km or greater distance.
    LT_25KM = 2         # < 25 km
    LT_1KM = 8          # < 1 km
    LT_0_25KM = 10      # < 0.25 km
    ACCEPTABLE = 8      # The minimum confidence accepted as good.
    EXACT = 100         # The user selected the position manually on the map.
    CONFIRMED = 101     # A supervisor selected the position manually on the map.


class TrackingModel(models.Model):
    """
    An abstract model that adds fields allowing tracking of activity related to
    the child model's instances, such as deletion or confirmation of the data.
    """
    deleted_on = models.DateTimeField(
        _("deleted on"),
        default=None, blank=True, null=True)
    confirmed_on = models.DateTimeField(
        _("confirmed on"),
        default=None, blank=True, null=True)
    checked_on = models.DateTimeField(
        _("checked on"),
        default=None, blank=True, null=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("approved by"),
        blank=True, null=True,
        related_name='+', on_delete=models.SET_NULL)

    all_objects = TrackingManager()
    objects = NotDeletedManager()
    objects_raw = NotDeletedRawManager()

    class Meta:
        abstract = True
        base_manager_name = 'all_objects'

    def set_check_status(self, set_by_user, clear_only=False, commit=True):
        """
        Updates the confirmation status. When set by the owner, clears the
        confirmation since this indicates update of data. Otherwise, sets
        the confirmation to now.
        The `clear_only` flag can be used for partial updates of the model by
        a supervisor, that should not indicate the whole model as confirmed.
        """
        if self.owner.user != set_by_user:
            if not clear_only:
                self.checked_on, self.checked_by = timezone.now(), set_by_user
        else:
            self.checked_on, self.checked_by = None, None
        if commit:
            self.save(update_fields=['checked_on', 'checked_by'])
        return self.checked_on, self.checked_by


class VisibilitySettings(models.Model):
    """
    Contains flags for visibility of objects in various venues: online or in
    the book. Can be linked via a generic foreign key to multiple model types.
    """
    DEFAULT_TYPE = pgettext_lazy("Noun", "Unknown")
    model_type = models.CharField(
        _("type"),
        max_length=25, default=DEFAULT_TYPE)
    model_id = models.PositiveIntegerField(
        _("content id"),
        null=True)
    content_type = models.ForeignKey(
        ContentType, verbose_name=_("content type"),
        on_delete=models.CASCADE)
    content_object = GenericForeignKey(
        'content_type', 'model_id', for_concrete_model=False)

    # The object should be viewable by any authenticated user.
    visible_online_public = models.BooleanField(_("visible online for all"))
    # The object should be viewable only by users who were explicitly granted
    # permission (authorized_users in the Place model).
    visible_online_authed = models.BooleanField(_("visible online w/authorization"))
    # The object should be printed in the paper edition.
    visible_in_book = models.BooleanField(_("visible in the book"))

    class Meta:
        verbose_name = _("visibility settings")
        verbose_name_plural = _("visibility settings")

    @classonlymethod
    def prep(cls, parent=None):
        """
        Instantiates new specific visibility settings according to the defaults
        specified in the proxy model. Immediately updates the database.
        The 'class-only method' decorator protects this from being hazardously
        called in templates, with unpleasant consequences.
        """
        try:
            container = apps.get_model(cls._CONTAINER_MODEL)
        except AttributeError:
            raise TypeError("Only specific visibility settings may be created") from None
        if parent:
            assert hasattr(parent, '_state'), (
                "{!r} is not a Model instance!".format(parent))
            assert isinstance(parent, container), (
                "{!r} is not a {}.{}!".format(parent, container.__module__, container.__name__))
        initial = {'{}{}'.format(cls._PREFIX, field): value for field, value in cls.defaults.items()}
        return cls.objects.create(
            model_id=getattr(parent, 'pk', None),
            model_type=cls.type(),
            content_type=ContentType.objects.get_for_model(container),
            **initial
        )

    def as_specific(self):
        """
        Converts the base model instance into a proxy model instance, e.g. for
        accessing the specific rules (objects returned from the database are
        always of the base model). All proxy models are expected to follow the
        "<BaseName>For<Type>" naming convention.
        """
        if self._meta.proxy:
            return self
        specific_name = "{base}For{narrow_type}".format(
            base=self.__class__.__name__, narrow_type=self.model_type)
        try:
            specific_class = globals()[specific_name]
        except KeyError as e:
            raise NameError(e)
        self.__class__ = specific_class
        return self

    @classmethod
    def specific_models(cls):
        """
        Returns a dictionary {name:class} of the available proxy models.
        """
        if cls._meta.proxy:
            cls = cls.__mro__[1]
        return {
            n[len(cls.__name__+'For'):] : c  # noqa: E203
            for n, c in globals().items()
            if n.startswith(cls.__name__+'For')
        }

    @classmethod
    def type(cls):
        """
        Used for initiating the `model_type` field according to class name
        suffix.  Any logic changes should be reflected in a data migration
        for existing values of the field.
        """
        if not cls._meta.proxy:
            raise TypeError("Model type is only defined for specific visibility settings")
        return cls.__name__[len(cls.__mro__[1].__name__+'For'):]

    @property
    def printable(self):
        """Can this data appear in the printed edition?"""
        return True

    @property
    def concealed(self):
        """Can this data be seen by anyone apart from owner and supervisors?"""
        return not any([self.visible_online_public, self.visible_online_authed, self.visible_in_book])

    _PREFIX = 'visible_'

    @classmethod
    def venues(cls):
        """
        Returns the list of available venues as strings:
          - online_public (authenticated users)
          - online_authed (authenticated and authorized users)
          - in_book       (printed edition users)
        """
        return [
            f.name[len(cls._PREFIX):] for f in cls._meta.get_fields() if f.name.startswith(cls._PREFIX)
        ]

    def __getitem__(self, venue):
        try:
            return getattr(self, self._PREFIX+venue)
        except Exception:
            raise KeyError("Unknown venue {!r}".format(venue))

    def __setitem__(self, venue, value):
        self[venue]  # This will raise an exception if venue is invalid.
        setattr(self, self._PREFIX+venue, value)

    def __str__(self):
        model_name = " ".join(camel_case_split(str(self.model_type))).lower()
        return str(_("Settings of visibility for {type}")).format(type=_(model_name))

    def __repr__(self):
        with override_translation(None):
            return "<{} {}@{} ~ OP:{},OA:{},B:{}>".format(
                self.__class__.__name__,
                "for {}".format(self.model_type) if not self._meta.proxy else "",
                repr(self.content_object),
                str(self.visible_online_public)[0],
                str(self.visible_online_authed)[0],
                str(self.visible_in_book)[0]
            )


class VisibilitySettingsForPlace(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Place'
    # Defaults contain the presets of visibility prior to user's customization.
    # Changes to the defaults must be reflected in a data migration.
    defaults = dict(online_public=True, online_authed=True, in_book=True)
    # Rules define what can be customized by the user. Tied online means an object
    # hidden for public will necessarily be hidden also for authorized users.
    rules = dict(online_public=True, online_authed=False, in_book=True, tied_online=True)

    @cached_property
    def printable(self):
        return (
            self.content_object.available
            and self.content_object.in_book
            and not self.content_object.deleted_on
        )


class VisibilitySettingsForFamilyMembers(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Place'
    defaults = dict(online_public=False, online_authed=True, in_book=True)
    rules = dict(online_public=True, online_authed=False, in_book=False)

    @cached_property
    def printable(self):
        return (
            self.content_object.available
            and self.content_object.in_book
            and not self.content_object.deleted_on
        )


class VisibilitySettingsForPhone(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Phone'
    defaults = dict(online_public=False, online_authed=True, in_book=True)
    rules = dict(online_public=True, online_authed=True, in_book=True)

    @cached_property
    def printable(self):
        return self.content_object.owner.has_places_for_hosting


class VisibilitySettingsForPublicEmail(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Profile'
    defaults = dict(online_public=False, online_authed=False, in_book=True)
    rules = dict(online_public=True, online_authed=True, in_book=False)

    @cached_property
    def printable(self):
        return self.content_object.has_places_for_hosting


class Profile(TrackingModel, TimeStampedModel):
    INCOGNITO = pgettext_lazy("Name", "Anonymous")

    class Titles(models.TextChoices):
        MRS = 'Mrs', _("Mrs")
        MR = 'Mr', _("Mr")

        __empty__ = ""

    class Pronouns(models.TextChoices):
        FEMININE = 'She', pgettext_lazy("Personal Pronoun", "she")
        MASCULINE = 'He', pgettext_lazy("Personal Pronoun", "he")
        NEUTRAL = 'They', pgettext_lazy("Personal Pronoun", "they")
        NEUTRAL_ALT = 'Ze', pgettext_lazy("Personal Pronoun", "ze")
        NEUTRAL_OR_F = 'They/She', pgettext_lazy("Personal Pronoun", "they or she")
        NEUTRAL_OR_M = 'They/He', pgettext_lazy("Personal Pronoun", "they or he")
        NEUTRAL_ALT_OR_F = 'Ze/She', pgettext_lazy("Personal Pronoun", "ze or she")
        NEUTRAL_ALT_OR_M = 'Ze/He', pgettext_lazy("Personal Pronoun", "ze or he")
        ANY = 'Any', pgettext_lazy("Personal Pronoun", "any")

        __empty__ = ""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(
        _("title"),
        blank=True,
        max_length=5, choices=Titles.choices)
    first_name = models.CharField(
        _("first name"),
        blank=True,
        max_length=255,
        validators=[validate_not_too_many_caps, validate_no_digit, validate_latin])
    last_name = models.CharField(
        _("last name"),
        blank=True,
        max_length=255,
        validators=[validate_not_too_many_caps, validate_no_digit, validate_latin])
    names_inversed = models.BooleanField(
        _("names in inverse order"),
        default=False)
    gender = SuggestiveField(
        _("gender"),
        blank=True,
        choices='hosting.Gender', to_field='name',
        db_column='gender_value',
        help_text=_("Also known as \"social sex identity\". Type your "
                    "own preference or select one of the suggestions."))
    pronoun = models.CharField(
        _("personal pronoun"),
        blank=True,
        max_length=10, choices=Pronouns.choices)
    birth_date = models.DateField(
        _("birth date"),
        null=True, blank=True,
        validators=[TooFarPastValidator(200), validate_not_in_future],
        help_text=_("In the format year(4 digits)-month(2 digits)-day(2 digits)."))
    death_date = models.DateField(
        _("death date"),
        null=True, blank=True,
        validators=[validate_not_in_future],
        help_text=_("In the format year(4 digits)-month(2 digits)-day(2 digits)."))
    email = StyledEmailField(
        _("public email"),
        blank=True,
        help_text=_("This email address will be used for the book. "
                    "Leave blank if you don't want this email to be public.\n"
                    "The system will never send emails to this address, "
                    "neither publish it on the site without your permission."))
    email_visibility = models.OneToOneField(
        'hosting.VisibilitySettingsForPublicEmail',
        related_name='%(class)s', on_delete=models.PROTECT)
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Short biography. \n"
                    "Provide here further details about yourself. "
                    "If you indicated that your gender is non-binary, "
                    "it will be helpful if you explain more."))
    avatar = models.ImageField(
        _("avatar"),
        blank=True,
        upload_to=RenameAndPrefixAvatar("avatars"),
        validators=[validate_image, validate_size],
        help_text=_("Small image under 100kB. Ideal size: 140x140 px."))

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    @property
    def owner(self):
        return self

    @property
    def full_name(self):
        """
        The combination of person's names, in the correct order.
        """
        if not self.names_inversed:
            combined_name = (self.first_name, self.last_name)
        else:
            combined_name = (self.last_name, self.first_name)
        real_name = " ".join(combined_name).strip()
        return real_name

    @property
    def name(self):
        return self.first_name.strip()

    @property
    def age(self):
        break_date = self.death_date if self.death_date else date.today()
        return int((break_date - self.birth_date).days / 365.24)

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url') and self.avatar_exists():
            return self.avatar.url
        else:
            email = self.user.email if self.user_id else "family.member@pasportaservo.org"
            email = value_without_invalid_marker(email)
            return email_to_gravatar(email, settings.DEFAULT_AVATAR_URL)

    def avatar_exists(self):
        return self.avatar and self.avatar.storage.exists(self.avatar.name)

    @property
    def icon(self):
        title = self.get_title_display().capitalize()
        template = '<span class="fa fa-user" title="{title}" aria-label="{title}"></span>'
        return format_html(template, title=title)

    def get_fullname_display(self, quote='"', non_empty=False):
        """
        The combination of person's names, in the correct order, for use in
        HTML pages. The `non_empty` flag ensures that something is output also
        for profiles without a user account (i.e., family members).
        """
        template_first_name = '<span class={q}first-name{q}>{name}</span>'
        template_last_name = '<span class={q}last-name{q}>{name}</span>'
        template_username = '<span class={q}profile-noname{q}>{name}</span>'
        template = []
        if self.first_name.strip():
            template.append((template_first_name, self.first_name))
        if self.last_name.strip():
            template.append((template_last_name, self.last_name))
        if not template:
            template.append((
                template_username,
                self.user.username.title() if self.user_id else ('--' if non_empty else " ")
            ))
        output = [format_html(t, q=mark_safe(quote), name=n) for (t, n) in template]
        if self.names_inversed:
            output.reverse()
        return mark_safe('&ensp;'.join(output))

    get_fullname_always_display = partialmethod(get_fullname_display, non_empty=True)

    def get_pronoun_parts(self):
        return self.get_pronoun_display().split(maxsplit=3)

    @property
    def autoslug(self):
        slugify = Slugify(to_lower=True, pretranslate={'ĉ': 'ch', 'ĝ': 'gh', 'ĥ': 'hh', 'ĵ': 'jh', 'ŝ': 'sh'})
        return slugify(self.name) or '--'

    @cached_property
    def _listed_places(self):
        fields = (
            'id',
            # host's offer (hosting/meeting):
            'available', 'tour_guide', 'have_a_drink',
            # in printed edition?
            'in_book',
            # visibility preferences:
            'visibility__visible_online_public', 'visibility__visible_in_book',
            # verification status:
            'confirmed', 'checked',
        )
        objects = self.owned_places.filter(deleted=False).values(*fields)
        return tuple(namedtuple('SimplePlaceContainer', place.keys())(*place.values()) for place in objects)

    def _count_listed_places(self, attr, query, restrained_search, **kwargs):
        cached = self.__dict__.setdefault('_host_offer_cache', {}).get(attr) if not len(kwargs) else None
        if not cached:
            try:
                _filter = {
                    'hosting': HostingFilter,
                    'meeting': MeetingFilter,
                    'accepting_guests': OkForGuestsFilter,
                    'in_book': InBookFilter,
                    'ok_for_book': OkForBookFilter,
                }[query](restrained_search, **kwargs)
            except KeyError:
                raise AttributeError("Query '%s' is not implemented for model Profile" % query)
            else:
                cached = len([p.id for p in self._listed_places if _filter(p)])
            if not len(kwargs):
                self._host_offer_cache[attr] = cached
        return cached

    @property
    def places_confirmed(self):
        return all(p.confirmed for p in self.owned_places.filter(deleted=False, in_book=True))

    def __getattr__(self, attr):
        """
        This dynamic attribute access allows to query the status of the profile as a host.
        The following queries are supported:
            * is_hosting / has_places_for_hosting
            * is_meeting / has_places_for_meeting
            * is_accepting_guests / has_places_for_accepting_guests
            * is_in_book / has_places_for_in_book
            * is_ok_for_book
        """
        m = re.match(r'^(is|has_places_for)_([a-z_]+)$', attr)
        if not m:
            raise AttributeError("Attribute %s does not exist on model Profile" % attr)
        query = m.group(2).lower()
        restrained_search = m.group(1) == 'is'
        customizable_queries = {
            'ok_for_book': {'accept_confirmed': False, 'accept_approved': True},
        }
        if query in customizable_queries:
            return partial(self._count_listed_places, attr, query, restrained_search, **customizable_queries[query])
        else:
            return self._count_listed_places(attr, query, restrained_search)

    def __str__(self):
        if self.full_name:
            return self.full_name
        elif self.user_id:
            return '{} ({})'.format(str(self.INCOGNITO), self.user.username)
        return '--'

    def __lt__(self, other):
        return ((self.last_name < other.last_name)
                or (self.last_name == other.last_name and self.first_name < other.first_name))

    def __repr__(self):
        return "<{} #{}: {}>".format(self.__class__.__name__, self.id, self.__str__())

    def rawdisplay(self):
        return "{} ({})".format(self.__str__(), getattr(self.birth_date, 'year', "?"))

    def rawdisplay_phones(self):
        return ", ".join(phone.rawdisplay() for phone in self.phones.filter(deleted=False))

    def get_absolute_url(self):
        return reverse('profile_detail', kwargs={
            'pk': self.pk,
            'slug': getattr(self, 'slug', self.autoslug)})

    def get_edit_url(self):
        return reverse('profile_edit', kwargs={
            'pk': self.pk,
            'slug': getattr(self, 'slug', self.autoslug)})

    def get_admin_url(self):
        return reverse('admin:hosting_profile_change', args=(self.pk,))

    def confirm_all_info(self, confirm=True):
        """
        Confirms (or unconfirms) all confirmable objects for a profile.
        """
        now = timezone.now() if confirm else None
        self.confirmed_on = now
        with transaction.atomic():
            self.owned_places.filter(deleted=False).update(confirmed_on=now)
            self.phones.filter(deleted=False).update(confirmed_on=now)
            self.website_set.filter(deleted=False).update(confirmed_on=now)
            self.save()
    confirm_all_info.alters_data = True

    @classonlymethod
    def get_basic_data(cls, request=None, **kwargs):
        """
        Returns only the strictly necessary data for determining if a profile exists and for
        building the profile's URLs. This avoids overly complicated DB queries.
        """
        if (
            request and (
                'user' in kwargs and kwargs['user'] == request.user
                or 'user_id' in kwargs and kwargs['user_id'] == request.user.pk)
        ):
            # When a profile is matched to the current user, attempt reusing the profile's
            # existence fact if already known.
            if getattr(request, 'user_has_profile', None) is False:
                raise cls.DoesNotExist
        qs = cls.all_objects.select_related(None).only('first_name', 'last_name', 'user_id')
        return qs.get(**kwargs)

    @classmethod
    def mark_invalid_emails(cls, emails):
        """
        Adds the 'invalid' marker to all email addresses in the given list.
        """
        models = {cls: None, get_user_model(): None}
        emails = emails or []
        for model in models:
            models[model] = (
                model.objects
                .filter(email__in=emails)
                .exclude(email='')
                .exclude(email__startswith=settings.INVALID_PREFIX)
                .update(email=Concat(V(settings.INVALID_PREFIX), F('email')))
            )
        return models

    @classmethod
    def mark_valid_emails(cls, emails):
        """
        Removes the 'invalid' marker from all email addresses in the given list.
        """
        models = {cls: None, get_user_model(): None}
        emails = emails or []
        for model in models:
            models[model] = (
                model.objects
                .filter(
                    email__in=emails,
                    email__startswith=settings.INVALID_PREFIX
                )
                .update(email=Substr(F('email'), len(settings.INVALID_PREFIX) + 1))
            )
        return models


class FamilyMember(Profile):
    class Meta:
        proxy = True

    @property
    def owner(self):
        """
        The current 'owner' of this profile.
        When a family member profile is a user on their own, the 'owner' is the
        user themselves.
        Otherwise, it is the 'owner' of the place currently being engaged with.
        """
        return self if self.user_id else getattr(self, '_current_owner', None)

    @owner.setter
    def owner(self, value):
        """
        Sets the current 'owner' of this profile.
        A family member profile may be associated with several places.
        When engaging with a specific place, the 'owner' would be the
        one of the place.
        Ignored if the family member is a user on their own.
        """
        if not isinstance(value, Profile):
            raise ValueError("An owner shall be a Profile.")
        if not self.user_id:
            setattr(self, '_current_owner', value)


class Place(TrackingModel, TimeStampedModel):
    owner = models.ForeignKey(
        'hosting.Profile', verbose_name=_("owner"),
        related_name="owned_places", on_delete=models.CASCADE)
    address = models.TextField(
        _("address"),
        blank=True,
        help_text=_("e.g.: Nieuwe Binnenweg 176"))
    city = models.CharField(
        _("city"),
        blank=True,
        max_length=255,
        validators=[validate_not_all_caps, validate_not_too_many_caps],
        help_text=_("Name in the official language, in latin letters; "
                    "not in Esperanto (e.g.:&nbsp;Rotterdam)."))
    closest_city = models.CharField(
        _("closest big city"),
        blank=True,
        max_length=255,
        validators=[validate_not_all_caps, validate_not_too_many_caps],
        help_text=_("If your place is in a town near a bigger city. "
                    "Name in the official language, in latin letters; not in Esperanto."))
    postcode = models.CharField(
        _("postcode"),
        blank=True,
        max_length=11)
    state_province = models.CharField(
        _("State / Province"),
        blank=True,
        max_length=70)
    country = CountryField(
        _("country"))
    location = PointField(
        _("location"), srid=SRID,
        null=True, blank=True)
    location_confidence = models.PositiveSmallIntegerField(
        _("confidence"),
        default=0)
    latitude = models.FloatField(
        _("latitude"),
        null=True, blank=True)
    longitude = models.FloatField(
        _("longitude"),
        null=True, blank=True)
    max_guest = RangeIntegerField(
        _("maximum number of guests"),
        min_value=1, max_value=50,
        null=True, blank=True,
        help_text=_("Leave empty if there is no limitation."))
    max_night = RangeIntegerField(
        _("maximum number of nights"),
        min_value=1, max_value=180,
        null=True, blank=True,
        help_text=_("Leave empty if there is no limitation."))
    contact_before = models.PositiveSmallIntegerField(
        _("contact this number of days in advance"),
        null=True, blank=True,
        help_text=_("Number of days before people should contact host."))
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Description or remarks about your place and its surroundings. "
                    "Consider that your guests, for example, might have an allergy "
                    "for animal fur or an arachnophobia, or have trouble scaling "
                    "multiple flights of stairs."))
    short_description = models.CharField(
        _("short description"),
        blank=True,
        max_length=140,
        help_text=_("Used in the book and on profile, 140 characters maximum."))
    available = models.BooleanField(
        _("available"),
        default=True,
        help_text=_("Is there a place to sleep on offer. If yes, you will be considered as host."))
    in_book = models.BooleanField(
        _("print in book"),
        default=True,
        help_text=_("If you want this place to be in the printed book. Must be available."))
    tour_guide = models.BooleanField(
        _("tour guide"),
        default=False,
        help_text=_("If you are ready to show your area to visitors."))
    have_a_drink = models.BooleanField(
        _("have a drink"),
        default=False,
        help_text=_("If you are ready to have a coffee or beer with visitors."))
    sporadic_presence = models.BooleanField(
        _("irregularly present"),
        default=False,
        help_text=_("If you are not often at this address and need an advance notification."))
    conditions = models.ManyToManyField(
        'hosting.Condition', verbose_name=_("conditions"),
        blank=True,
        help_text=_("You are welcome to expand on the conditions "
                    "in your home in the description."))
    family_members = models.ManyToManyField(
        'hosting.Profile', verbose_name=_("family members"),
        blank=True)
    family_members_visibility = models.OneToOneField(
        'hosting.VisibilitySettingsForFamilyMembers',
        related_name='family_members', on_delete=models.PROTECT)
    blocked_from = models.DateField(
        _("unavailable from"),
        null=True, blank=True,
        help_text=_("In the format year(4 digits)-month(2 digits)-day(2 digits)."))
    blocked_until = models.DateField(
        _("unavailable until"),
        null=True, blank=True,
        help_text=_("In the format year(4 digits)-month(2 digits)-day(2 digits)."))
    authorized_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, verbose_name=_("authorized users"),
        blank=True,
        help_text=_("List of users authorized to view most of data of this accommodation."))
    visibility = models.OneToOneField(
        'hosting.VisibilitySettingsForPlace',
        related_name='%(class)s', on_delete=models.PROTECT)

    available_objects = AvailableManager()

    class Meta:
        verbose_name = _("place")
        verbose_name_plural = _("places")
        default_manager_name = 'all_objects'

    @property
    def profile(self):
        """Proxy for self.owner. Rename 'owner' to 'profile' if/as possible."""
        return self.owner

    @property
    def lat(self):
        if not self.location or self.location.empty:
            return 0
        return round(self.location.y, 2)

    @property
    def lng(self):
        if not self.location or self.location.empty:
            return 0
        return round(self.location.x, 2)

    @property
    def bbox(self):
        """
        Returns an OpenStreetMap-formatted bounding box.
        See http://wiki.osm.org/wiki/Bounding_Box
        """
        dx, dy = 0.007, 0.003  # Delta lng and delta lat around position
        if self.location and not self.location.empty:
            boundingbox = (self.lng - dx, self.lat - dy, self.lng + dx, self.lat + dy)
            return ",".join([str(coord) for coord in boundingbox])
        else:
            return ""

    @cached_property
    def subregion(self):
        try:
            region = CountryRegion.objects.get(country=self.country, iso_code=self.state_province)
        except CountryRegion.DoesNotExist:
            region = CountryRegion(country=self.country, iso_code='X-00', latin_code=self.state_province)
        region.save = lambda *args, **kwargs: None  # Read-only instance.
        return region

    @property
    def icon(self):
        template = ('<span class="fa ps-home-fh" title="{title}" '
                    '      data-toggle="tooltip" data-placement="left"></span>')
        return format_html(template, title=self._meta.verbose_name.capitalize())

    def family_members_cache(self):
        """
        Cached QuerySet of family members.
        (Direct access to the field in templates re-queries the database.)
        """
        cache_name = '_family_cache'
        try:
            cached_qs = self.__dict__[cache_name]
        except KeyError:
            try:
                cached_qs = self._prefetched_objects_cache[self.family_members.prefetch_cache_name]
            except (AttributeError, KeyError):
                cached_qs = self.family_members.order_by('birth_date').select_related('user')
            self.__dict__[cache_name] = cached_qs
        finally:
            return cached_qs

    @property
    def family_is_anonymous(self):
        """
        Returns True when there is only one family member, which does not have
        a name and is not a user of the website (profile without user account).
        """
        family = self.family_members_cache()
        return len(family) == 1 and not family[0].user_id and not family[0].full_name

    def authorized_users_cache(self, complete=True, also_deleted=False):
        """
        Cached QuerySet of authorized users.
        (Direct access to the field in templates re-queries the database.)
        - Flag `complete` fetches also profile data for each user record.
        - Flag `also_deleted` fetches records with deleted_on != NULL.
        """
        cache_name = '_authed{}{}_cache'.format(
            '_all' if also_deleted else '_active',
            '_complete' if complete else '',
        )
        try:
            cached_qs = self.__dict__[cache_name]
        except KeyError:
            cached_qs = self.authorized_users.all()
            if not also_deleted:
                cached_qs = cached_qs.filter(profile__deleted_on__isnull=True)
            if complete:
                cached_qs = cached_qs.select_related('profile').defer('profile__description')
            self.__dict__[cache_name] = cached_qs
        finally:
            return cached_qs

    def conditions_cache(self):
        """
        Cached QuerySet of place conditions.
        (Direct access to the field in templates re-queries the database.)
        """
        return self.__dict__.setdefault('_conditions_cache', self.conditions.all())

    @property
    def owner_available(self):
        return self.tour_guide or self.have_a_drink

    @property
    def is_blocked(self):
        return any([self.blocked_until and self.blocked_until >= date.today(),
                    self.blocked_from and not self.blocked_until])

    def get_absolute_url(self):
        return reverse('place_detail', kwargs={'pk': self.pk})

    def get_locality_display(self):
        """
        Returns "city (country)" or just "country" when no city is given.
        """
        if self.city:
            return format_lazy("{city} ({state})", city=self.city, state=self.country.name)
        else:
            return self.country.name

    def get_postcode_display(self):
        try:
            return self._postcode_display_cache
        except AttributeError:
            pass

        if self.postcode:
            postcode_prefix = COUNTRIES_DATA.get(self.country.code, {}).get('postal_code_prefix')
            if postcode_prefix and not self.postcode.startswith(postcode_prefix):
                display_value = f'{postcode_prefix}{self.postcode}'
            else:
                display_value = self.postcode
        else:
            display_value = ""
        self._postcode_display_cache = display_value
        return display_value

    def __setattr__(self, name, value):
        if name == 'postcode':
            try:
                del self._postcode_display_cache
            except AttributeError:
                pass
        if name == 'state_province':
            try:
                del self.subregion
            except AttributeError:
                pass
        super().__setattr__(name, value)

    def __str__(self):
        return ", ".join([self.city, str(self.country.name)]) if self.city else str(self.country.name)

    def __repr__(self):
        return "<{} #{}: {}>".format(self.__class__.__name__, self.id, self.__str__())

    def rawdisplay_family_members(self):
        family_members = self.family_members.exclude(pk=self.owner_id).order_by('birth_date')
        return ", ".join(fm.rawdisplay() for fm in family_members)

    def rawdisplay_conditions(self):
        return ", ".join(c.__str__() for c in self.conditions.all())


class Phone(TrackingModel, TimeStampedModel):

    class PhoneType(models.TextChoices):
        MOBILE = 'm', pgettext_lazy("Phone Type", "mobile")
        HOME = 'h', pgettext_lazy("Phone Type", "home")
        WORK = 'w', pgettext_lazy("Phone Type", "work")
        FAX = 'f', pgettext_lazy("Phone Type", "fax")

    profile = models.ForeignKey(
        'hosting.Profile', verbose_name=_("profile"),
        related_name="phones", on_delete=models.CASCADE)
    number = PhoneNumberField(
        _("number"),
        help_text=_("International number format begining with the plus sign "
                    "(e.g.: +31 10 436 1044)"))
    country = CountryField(
        _("country"))
    comments = models.CharField(
        _("comments"),
        blank=True,
        max_length=255)
    type = models.CharField(
        _("phone type"),
        max_length=3,
        choices=PhoneType.choices, default=PhoneType.MOBILE)
    visibility = models.OneToOneField(
        'hosting.VisibilitySettingsForPhone',
        related_name='%(class)s', on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("phone")
        verbose_name_plural = _("phones")
        unique_together = ('profile', 'number')
        order_with_respect_to = 'profile'

    @property
    def owner(self):
        return self.profile

    @property
    def icon(self):
        match self.type:
            case self.PhoneType.WORK:
                cls = "ps-phone"
            case self.PhoneType.MOBILE:
                cls = "ps-mobile-phone"
            case self.PhoneType.FAX:
                cls = "ps-fax"
            case _:  # PhoneType.HOME or ''
                cls = "ps-old-phone"
        title = self.get_type_display().capitalize() or _("type not indicated")
        template = ('<span class="fa {cls}" title="{title}" '
                    '      data-toggle="tooltip" data-placement="left"></span>')
        return format_html(template, cls=cls, title=title)

    def __str__(self):
        """ as_e164             '+31104361044'
            as_international    '+31 10 436 1044'
            as_national         '010 436 1044'
            as_rfc3966          'tel:+31-10-436-1044'
        """
        return self.number.as_international

    def __repr__(self):
        return "<{}: {}{} |p#{}>".format(
            self.__class__.__name__,
            "("+self.type+") " if self.type else "", self.__str__(),
            self.profile_id
        )

    def rawdisplay(self):
        t = self.type or "(?)"
        return t + ": " + self.number.as_international


class Website(TrackingModel, TimeStampedModel):
    profile = models.ForeignKey('hosting.Profile', verbose_name=_("profile"), on_delete=models.CASCADE)
    url = models.URLField(_("URL"))

    class Meta:
        verbose_name = _("website")
        verbose_name_plural = _("websites")

    @property
    def owner(self):
        return self.profile

    def __str__(self):
        return self.url

    def __repr__(self):
        return "<{}: {} |p#{}>".format(
            self.__class__.__name__,
            self.__str__(),
            self.profile_id
        )


class Gender(models.Model):
    """Profile's possible gender."""
    name_en = models.CharField(
        _("name (in English)"),
        max_length=255, unique=True)
    name = models.CharField(
        _("name"),
        max_length=255, unique=True)

    class Meta:
        verbose_name = _("gender")
        verbose_name_plural = _("genders")

    def __eq__(self, other):
        if isinstance(other, Gender):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        else:
            return NotImplemented

    def __str__(self):
        return (
            self.name if str(get_language()).startswith('eo')
            else (self.name_en or self.name)
        )


class CountryRegion(models.Model):
    country = CountryField(
        _("country"))
    iso_code = models.CharField(
        _("ISO code"),
        max_length=4)
    latin_code = models.CharField(
        _("Normative code in latin letters"),
        blank=False,
        max_length=70)
    latin_name = models.CharField(
        _("Full name in latin letters"),
        blank=True,
        max_length=70)
    local_code = models.CharField(
        _("Normative code in local language"),
        blank=True,
        max_length=70)
    local_name = models.CharField(
        _("Full name in local language"),
        blank=True,
        max_length=70)
    esperanto_name = models.CharField(
        _("Name in Esperanto"),
        blank=True,
        max_length=70)

    class Meta:
        verbose_name = _("subregion")
        verbose_name_plural = _("subregions")
        unique_together = ('country', 'iso_code')
        indexes = [
            models.Index(fields=['country', 'iso_code', 'id'], name='countryregion_isocode_pk_idx'),
        ]

    @property
    def translated_name(self):
        return self.esperanto_name if str(get_language()).startswith('eo') else ""

    @property
    def translated_or_latin_name(self):
        return self.translated_name or self.latin_name or self.latin_code

    def get_display_value(self, with_esperanto=False):
        """
        Returns the name of the region in the format Esperanto name -- Latin name (Local name),
        where only the latin name is mandated and the other parts are optional, included if
        specified.
        """
        try:
            return self._display_value_cache[with_esperanto]
        except AttributeError:
            self._display_value_cache = {}
        except KeyError:
            pass

        local_region = self.local_name or self.local_code
        latin_region = self.latin_name or self.latin_code
        if local_region:
            try:
                validate_latin(local_region)
                if (local_region != latin_region
                        and local_region not in latin_region
                        and latin_region not in local_region
                        and unidecode(local_region) != latin_region):
                    # Sometimes the difference between the local and the main names is
                    # only in the diacritical marks or the addition of "Province of".
                    raise UnicodeError
            except Exception:
                # If the local name is not in latin letters or different from the
                # main name, display both of them.
                native_name = f'{latin_region} ({local_region})'
            else:
                # When the local name is mostly identical (except for the diacritical
                # marks) to the main name, display only the local name.
                native_name = local_region
        else:
            native_name = latin_region
        if self.esperanto_name and with_esperanto:
            display_value = f'{self.esperanto_name}  –  {native_name}'
        else:
            display_value = native_name

        self._display_value_cache[with_esperanto] = display_value
        return display_value

    get_display_value_with_esperanto = partialmethod(get_display_value, with_esperanto=True)

    def __str__(self):
        return "{}: {}".format(
            self.country.code,
            f"{self.latin_name} ({self.latin_code})" if self.latin_name else self.latin_code
        )


class Whereabouts(models.Model):
    WHEREABOUTS_TYPE_CHOICES = (
        (LocationType.CITY.value, _("City")),
        (LocationType.REGION.value, _("State / Province")),
    )

    type = models.CharField(
        _("location type"),
        max_length=1,
        choices=WHEREABOUTS_TYPE_CHOICES)
    name = models.CharField(
        _("name"),
        blank=False,
        max_length=255,
        help_text=_("Name in the official language, in latin letters; "
                    "not in Esperanto (e.g.:&nbsp;Rotterdam)."))
    state = models.CharField(
        _("State / Province"),
        blank=True,
        max_length=70)
    country = CountryField(
        _("country"))
    bbox = LineStringField(
        _("bounding box"), srid=SRID,
        help_text=_("Expected diagonal: south-west lon/lat, north-east lon/lat."))
    center = PointField(
        _("geographical center"), srid=SRID,
        help_text=_("Expected: longitude/latitude position."))

    class Meta:
        verbose_name = pgettext_lazy("name::singular", "whereabouts")
        verbose_name_plural = pgettext_lazy("name::plural", "whereabouts")

    def __str__(self):
        return str(_("Location of {landmark} ({state})")).format(
            landmark=self.name,
            state=", ".join(filter(None, [self.state, str(self.country.name)]))
        )

    def __repr__(self):
        return "<{}: {} ~ SW{} NE{}>".format(
            self.__class__.__name__,
            ", ".join(filter(None, [self.name, self.state, self.country.name])),
            self.bbox.coords[0], self.bbox.coords[1]
        )


class Condition(models.Model):
    """
    Hosting condition in a place (e.g. bringing sleeping bag, no smoking...).
    """
    class Categories(models.TextChoices):
        IN_THE_HOUSE = (
            'in_house',
            pgettext_lazy("Condition Category", "in the house")
        )
        SLEEPING_CONDITIONS = (
            'sleeping_cond',
            pgettext_lazy("Condition Category", "sleeping conditions")
        )
        ON_THE_OUTSIDE = (
            'outside_house',
            pgettext_lazy("Condition Category", "outside the house")
        )

    category = models.CharField(
        _("category"),
        blank=False,
        max_length=15, choices=Categories.choices)
    name_en = models.CharField(
        _("name (in English)"),
        max_length=255,
        # Translators: English language example for condition's `name_en`.
        help_text=_("E.g.: 'Don't smoke'."))
    name = models.CharField(
        _("name"),
        max_length=255,
        # Translators: Esperanto language example for condition's `name`.
        help_text=_("E.g.: 'Ne fumu'."))
    abbr = models.CharField(
        _("abbreviation"),
        max_length=20,
        blank=True,
        help_text=_("Official abbreviation as used in the book. E.g.: 'Nef.'"))
    icon = models.TextField(
        _("icon"))
    restriction = models.BooleanField(
        _("is a limitation"),
        default=True,
        help_text=_("Marked = restriction for the guests, "
                    "unmarked = facilitation for the guests."))

    class Meta:
        verbose_name = _("condition")
        verbose_name_plural = _("conditions")

    @classmethod
    def active_name_field(cls):
        return 'name' if str(get_language()).startswith('eo') else 'name_en'

    def __str__(self):
        return getattr(self, self.active_name_field())

    def get_absolute_url(self):
        return reverse('hosting_condition_detail', kwargs={'pk': self.pk})


class ContactPreference(models.Model):
    """
    Contact preference for a profile: whether by email, telephone or snail mail.
    """
    name = models.CharField(
        _("name"),
        max_length=255)

    class Meta:
        verbose_name = _("contact preference")
        verbose_name_plural = _("contact preferences")

    def __str__(self):  # pragma: no cover
        return self.name


class Preferences(models.Model):
    """Profile's various general preferences, that relate to the account as a whole."""
    profile = models.OneToOneField(
        'hosting.Profile', verbose_name=_("profile"),
        related_name="pref", on_delete=models.CASCADE)
    contact_preferences = models.ManyToManyField(
        'hosting.ContactPreference', verbose_name=_("contact preferences"),
        blank=True)
    site_analytics_consent = models.BooleanField(
        _("I agree to be included by usage measurement tools."),
        default=None, null=True,
        help_text=_("These technologies help us to improve Pasporta Servo. Through them "
                    "we collect information about how visitors interact with the "
                    "web site and which changes will make the interaction better."))
    public_listing = models.BooleanField(
        _("List my profile in search results open to the internet."),
        default=True)

    class Meta:
        verbose_name = _("preferences for profile")
        verbose_name_plural = _("preferences for profile")

    def __str__(self):  # pragma: no cover
        return ''

    def __repr__(self):
        return "<{}|p#{}>".format(
            self.__class__.__name__,
            self.profile_id
        )


class TravelAdvice(TimeStampedModel):
    content = SimpleMDEField(
        _("Markdown content"),
        simplemde_options={
            'hideIcons': ['heading', 'quote', 'unordered-list', 'ordered-list', 'image'],
            'spellChecker': False,
        })
    description = models.TextField(
        _("HTML description"),
        blank=False)
    countries = CountryField(
        _("countries"),
        multiple=True,
        blank_label=_("- ALL COUNTRIES -"),
        blank=True)
    active_from = models.DateField(
        _("advice valid from date"),
        null=True, blank=True)
    active_until = models.DateField(
        _("advice valid until date"),
        null=True, blank=True)

    objects = ActiveStatusManager()

    class Meta:
        verbose_name = _("travel advice")
        verbose_name_plural = _("travel advices")

    def trimmed_content(self, cut_off=70):
        return '{}...'.format(self.content[:cut_off-2]) if len(self.content) > cut_off else self.content

    def applicable_countries(self, all_label=None, code=True):
        if not self.countries:
            return all_label or self._meta.get_field('countries').blank_label
        else:
            return ', '.join(c.code if code else c.name for c in self.countries)

    @classmethod
    def get_for_country(cls, country_code, is_active=True):
        """
        Extracts advices indicated for a specific country, i.e., those applicable to a
        list of countries among which is the queried country, or those applicable to
        any country. If `is_active` is True or None, also verifies whether the advice
        is current or just applicable, correspondingly. However, if `is_active` is
        False, only advices for this specific country which are not anymore or not yet
        valid are returned.
        """
        lookups = Q(countries__regex=r'(^|,){}(,|$)'.format(country_code))
        if is_active is False:
            lookups = lookups & Q(is_active=False)
        else:
            lookups = lookups | Q(countries='')
            if is_active is not None:
                lookups = lookups & Q(is_active=True)
        return cls.objects.filter(lookups).order_by('-active_until', '-id')

    def __str__(self):
        return ' '.join((
            self.trimmed_content().replace('\n', ' '),
            '({})'.format(self.applicable_countries())
        ))

    def __repr__(self):
        return "<TravelAdvice for {}: {}>".format(
            self.applicable_countries("ALL"),
            self.trimmed_content(90).replace('\n', ' ')
        )

    def save(self, *args, **kwargs):
        self.description = commonmark(self.content)
        return super().save(*args, **kwargs)
    save.alters_data = True
