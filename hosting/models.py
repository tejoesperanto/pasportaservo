from datetime import date

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models import PointField
from django.db import models, transaction
from django.db.models import F, Q, Value as V
from django.db.models.functions import Concat, Substr
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from django_countries.fields import CountryField
from django_extensions.db.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField
from slugify import Slugify

from core.utils import camel_case_split

from .fields import StyledEmailField
from .gravatar import email_to_gravatar
from .managers import AvailableManager, NotDeletedManager, TrackingManager
from .utils import UploadAndRenameAvatar, value_without_invalid_marker
from .validators import (
    TooFarPastValidator, validate_image, validate_latin,
    validate_no_digit, validate_not_all_caps, validate_not_in_future,
    validate_not_too_many_caps, validate_size,
)

MRS, MR = 'Mrs', 'Mr'
TITLE_CHOICES = (
    (None, ""),
    (MRS, _("Mrs")),
    (MR, _("Mr")),
)

MOBILE, HOME, WORK, FAX = 'm', 'h', 'w', 'f'
PHONE_TYPE_CHOICES = (
    (MOBILE, _("mobile")),
    (HOME, _("home")),
    (WORK, _("work")),
    (FAX, _("fax")),
)


class TrackingModel(models.Model):
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

    class Meta:
        abstract = True

    def set_check_status(self, set_by_user, clear_only=False, commit=True):
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
    DEFAULT_TYPE = 'Unknown'
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

    @classmethod
    def _prep(cls, parent=None):
        """
        Instantiates new specific visibility settings according to the defaults
        specified in the proxy model. Immediately updates the database.
        Due to this being a class method, the leading underscore in the method
        name protects it from being hazardously called in templates.
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
        model_name = " ".join(camel_case_split(self.model_type)).lower()
        return str(_("Settings of visibility for {type}")).format(type=_(model_name))

    def __repr__(self):
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
    rules = dict(online_public=False, online_authed=False, in_book=True, tied_online=True)
    # TODO: online_public=True

    @cached_property
    def printable(self):
        return self.content_object.available


class VisibilitySettingsForFamilyMembers(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Place'
    defaults = dict(online_public=False, online_authed=True, in_book=True)
    rules = dict(online_public=True, online_authed=False, in_book=False)

    @cached_property
    def printable(self):
        return self.content_object.available


class VisibilitySettingsForPhone(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Phone'
    defaults = dict(online_public=False, online_authed=True, in_book=True)
    rules = dict(online_public=True, online_authed=True, in_book=True)

    @cached_property
    def printable(self):
        return self.content_object.owner.is_hosting


class VisibilitySettingsForPublicEmail(VisibilitySettings):
    class Meta:
        proxy = True
    _CONTAINER_MODEL = 'hosting.Profile'
    defaults = dict(online_public=False, online_authed=False, in_book=True)
    rules = dict(online_public=True, online_authed=True, in_book=False)

    @cached_property
    def printable(self):
        return self.content_object.is_hosting


class Profile(TrackingModel, TimeStampedModel):
    TITLE_CHOICES = TITLE_CHOICES
    INCOGNITO = pgettext_lazy("Name", "Anonymous")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(
        _("title"),
        blank=True,
        max_length=5, choices=TITLE_CHOICES)
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
    birth_date = models.DateField(
        _("birth date"),
        null=True, blank=True,
        validators=[TooFarPastValidator(200), validate_not_in_future],
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
        help_text=_("Short biography."))
    avatar = models.ImageField(
        _("avatar"),
        blank=True,
        upload_to=UploadAndRenameAvatar("avatars"),
        validators=[validate_image, validate_size],
        help_text=_("Small image under 100kB. Ideal size: 140x140 px."))
    contact_preferences = models.ManyToManyField(
        'hosting.ContactPreference', verbose_name=_("contact preferences"),
        blank=True)

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
        return int((date.today() - self.birth_date).days / 365.24)

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            email = self.user.email if self.user_id else "family.member@pasportaservo.org"
            email = value_without_invalid_marker(email)
            return email_to_gravatar(email, settings.DEFAULT_AVATAR_URL)

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
                self.user.username.title() if self.user else ('--' if non_empty else " ")
            ))
        output = [format_html(t, q=mark_safe(quote), name=n) for (t, n) in template]
        if self.names_inversed:
            output.reverse()
        return mark_safe('&ensp;'.join(output))

    get_fullname_always_display = lambda self: self.get_fullname_display(non_empty=True)

    @property
    def autoslug(self):
        slugify = Slugify(to_lower=True, pretranslate={'ĉ': 'ch', 'ĝ': 'gh', 'ĥ': 'hh', 'ĵ': 'jh', 'ŝ': 'sh'})
        return slugify(self.name) or '--'

    @property
    def is_hosting(self):
        return self.owned_places.filter(available=True, deleted=False).count()

    @property
    def is_meeting(self):
        return sum((p.owner_available for p in self.owned_places.filter(deleted=False)), 0)

    @property
    def is_in_book(self):
        return self.owned_places.filter(
            available=True, deleted=False, in_book=True,
        ).count()

    def is_ok_for_book(self, accept_confirmed=False, accept_approved=True):
        book_filter = Q(confirmed=True) if accept_confirmed else Q()
        book_filter |= Q(checked=True) if accept_approved else Q()
        return self.owned_places.filter(
            book_filter, available=True, in_book=True, deleted=False
        ).exists()

    @property
    def places_confirmed(self):
        return all(p.confirmed for p in self.owned_places.filter(deleted=False, in_book=True))

    def __str__(self):
        if self.full_name:
            return self.full_name
        elif self.user:
            return '{} ({})'.format(str(self.INCOGNITO), self.user.username)
        return '--'

    def __lt__(self, other):
        return ((self.last_name < other.last_name) or
                (self.last_name == other.last_name and self.first_name < other.first_name))

    def __repr__(self):
        return "<{} #{}: {}>".format(self.__class__.__name__, self.id, self.__str__())

    def rawdisplay(self):
        return "{} ({})".format(self.__str__(), getattr(self.birth_date, 'year', "?"))

    def rawdisplay_phones(self):
        return ", ".join(phone.rawdisplay() for phone in self.phones.all())

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
        """Confirm (or unconfirm) all confirmable objects for a profile."""
        now = timezone.now() if confirm else None
        self.confirmed_on = now
        with transaction.atomic():
            self.owned_places.filter(deleted=False).update(confirmed_on=now)
            self.phones.filter(deleted=False).update(confirmed_on=now)
            self.website_set.filter(deleted=False).update(confirmed_on=now)
            self.save()
    confirm_all_info.alters_data = True

    @classmethod
    def mark_invalid_emails(cls, emails=None):
        models = {cls: None, get_user_model(): None}
        for model in models:
            models[model] = (
                model.objects
                .filter(email__in=emails)
                .exclude(email__startswith=settings.INVALID_PREFIX)
                .update(email=Concat(V(settings.INVALID_PREFIX), F('email')))
            )
        return models
    mark_invalid_emails.do_not_call_in_templates = True

    @classmethod
    def mark_valid_emails(cls, emails=None):
        models = {cls: None, get_user_model(): None}
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
    mark_valid_emails.do_not_call_in_templates = True


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
        help_text=_("Name in the official language, not in Esperanto (e.g.: Rotterdam)"))
    closest_city = models.CharField(
        _("closest big city"),
        blank=True,
        max_length=255,
        validators=[validate_not_all_caps, validate_not_too_many_caps],
        help_text=_("If your place is in a town near a bigger city. "
                    "Name in the official language, not in Esperanto."))
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
        _("location"), srid=4326,
        null=True, blank=True)
    latitude = models.FloatField(
        _("latitude"),
        null=True, blank=True)
    longitude = models.FloatField(
        _("longitude"),
        null=True, blank=True)
    max_guest = models.PositiveSmallIntegerField(
        _("maximum number of guest"),
        null=True, blank=True)
    max_night = models.PositiveSmallIntegerField(
        _("maximum number of night"),
        null=True, blank=True)
    contact_before = models.PositiveSmallIntegerField(
        _("contact before"),
        null=True, blank=True,
        help_text=_("Number of days before people should contact host."))
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Description or remarks about your place."))
    short_description = models.CharField(
        _("short description"),
        blank=True,
        max_length=140,
        help_text=_("Used in the book and on profile, 140 characters maximum."))
    available = models.BooleanField(
        _("available"),
        default=True,
        help_text=_("If this place is searchable. If yes, you will be considered as host."))
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
        blank=True)
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
        """Return an OpenStreetMap formated bounding box.
        See http://wiki.osm.org/wiki/Bounding_Box
        """
        dx, dy = 0.007, 0.003  # Delta lng and delta lat around position
        boundingbox = (self.lng - dx, self.lat - dy, self.lng + dx, self.lat + dy)
        return ",".join([str(coord) for coord in boundingbox])

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
        return self.__dict__.setdefault('_family_cache', self.family_members.order_by('birth_date'))

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

    def __str__(self):
        return ", ".join([self.city, str(self.country.name)]) if self.city else str(self.country.name)

    def __repr__(self):
        return "<{} #{}: {}>".format(self.__class__.__name__, self.id, self.__str__())

    def rawdisplay_family_members(self):
        family_members = self.family_members.exclude(pk=self.owner_id).order_by('birth_date')
        return ", ".join(fm.rawdisplay() for fm in family_members)

    def rawdisplay_conditions(self):
        return ", ".join(c.__str__() for c in self.conditions.all())

    def latexdisplay_conditions(self):
        return r"\, ".join(c.latex for c in self.conditions.all())

    # GeoJSON properties

    @property
    def url(self):
        return self.get_absolute_url()

    @property
    def owner_name(self):
        return self.owner.name or self.owner.INCOGNITO

    @property
    def owner_url(self):
        return self.owner.get_absolute_url()


class Phone(TrackingModel, TimeStampedModel):
    PHONE_TYPE_CHOICES = PHONE_TYPE_CHOICES
    MOBILE, HOME, WORK, FAX = 'm', 'h', 'w', 'f'
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
        choices=PHONE_TYPE_CHOICES, default=MOBILE)
    visibility = models.OneToOneField(
        'hosting.VisibilitySettingsForPhone',
        related_name='%(class)s', on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("phone")
        verbose_name_plural = _("phones")
        unique_together = ('profile', 'number')

    @property
    def owner(self):
        return self.profile

    @property
    def icon(self):
        if self.type == self.WORK:
            cls = "ps-phone"
        elif self.type == self.MOBILE:
            cls = "ps-mobile-phone"
        elif self.type == self.FAX:
            cls = "ps-fax"
        else:  # self.HOME or ''
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


class Condition(models.Model):
    """Hosting condition (e.g. bringing sleeping bag, no smoking...)."""
    name = models.CharField(
        _("name"),
        max_length=255,
        help_text=_("E.g.: 'Ne fumu'."))
    abbr = models.CharField(
        _("abbreviation"),
        max_length=20,
        help_text=_("Official abbreviation as used in the book. E.g.: 'Nef.'"))
    slug = models.SlugField(
        _("URL friendly name"))

    class Meta:
        verbose_name = _("condition")
        verbose_name_plural = _("conditions")

    def __str__(self):
        return self.name


class ContactPreference(models.Model):
    """Contact preference for a profile, whether by email, telephone or snail mail."""
    name = models.CharField(
        _("name"),
        max_length=255)

    class Meta:
        verbose_name = _("contact preference")
        verbose_name_plural = _("contact preferences")

    def __str__(self):
        return self.name
