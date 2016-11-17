from datetime import date

from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.text import slugify
from django.db import models, transaction
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField
from django_countries.fields import CountryField, Country

from .managers import NotDeletedManager, WithCoordManager, AvailableManager
from .validators import (
    validate_not_all_caps, validate_not_too_many_caps, validate_no_digit,
    validate_not_in_future, TooFarPastValidator, TooNearPastValidator,
    validate_image, validate_size,
)
from .utils import UploadAndRenameAvatar
from .gravatar import email_to_gravatar


MRS, MR = 'Mrs', 'Mr'
TITLE_CHOICES = (
    (None, ""),
    (MRS, _("Mrs")),
    (MR, _("Mr")),
)

ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR = 5, 4, 3, 2, 1

MOBILE, HOME, WORK, FAX = 'm', 'h', 'w', 'f'
PHONE_TYPE_CHOICES = (
    (MOBILE, _("mobile")),
    (HOME, _("home")),
    (WORK, _("work")),
    (FAX, _("fax")),
)


class TrackingModel(models.Model):
    checked = models.BooleanField(_("checked"), default=False)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("approved by"), blank=True, null=True,
        related_name="+", limit_choices_to={'is_staff': True}, on_delete=models.SET_NULL)
    confirmed_on = models.DateTimeField(_("confirmed on"), default=None, blank=True, null=True)
    deleted = models.BooleanField(_("deleted"), default=False)

    all_objects = models.Manager()
    objects = NotDeletedManager()

    class Meta:
        abstract = True

    @property
    def confirmed(self):
        """If the confirmed_on date is more recent than several months."""
        if not self.confirmed_on:
            return False
        return (timezone.now() - self.confirmed_on) < settings.CONFIRMATION_VALIDITY_PERIOD


class Profile(TrackingModel, TimeStampedModel):
    TITLE_CHOICES = TITLE_CHOICES
    ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR = ADMIN, STAFF, SUPERVISOR, OWNER, VISITOR
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(_("title"), max_length=5, choices=TITLE_CHOICES, blank=True)
    first_name = models.CharField(_("first name"), max_length=255, blank=True,
        validators=[validate_not_too_many_caps, validate_no_digit])
    last_name = models.CharField(_("last name"), max_length=255, blank=True,
        validators=[validate_not_too_many_caps, validate_no_digit])
    birth_date = models.DateField(_("birth date"), blank=True, null=True,
        validators=[TooFarPastValidator(200), validate_not_in_future])
    description = models.TextField(_("description"), help_text=_("Short biography."), blank=True)
    avatar = models.ImageField(_("avatar"), upload_to=UploadAndRenameAvatar("avatars"), blank=True,
        validators=[validate_image, validate_size],
        help_text=_("Small image under 100kB. Ideal size: 140x140 px."))
    contact_preferences = models.ManyToManyField('hosting.ContactPreference', verbose_name=_("contact preferences"), blank=True)

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    @property
    def full_name(self):
        return " ".join((self.first_name, self.last_name)).strip()  \
               or (self.user.username.title() if self.user else " ")

    @property
    def name(self):
        return self.first_name or self.user.username.title()

    @property
    def anonymous_name(self):
        return " ".join((self.first_name, self.last_name[:1] + "." if self.last_name else "")).strip()  \
               or (self.user.username.title() if self.user else " ")

    @property
    def age(self):
        return int((date.today() - self.birth_date).days / 365.24)

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            email = self.user.email if self.user else "family.member@pasportaservo.org"
            return email_to_gravatar(email, settings.DEFAULT_AVATAR_URL)

    @property
    def icon(self):
        title = self.get_title_display().capitalize()
        template = '<span class="glyphicon glyphicon-user" title="{title}"></span>'
        return format_html(template, title=title)

    @property
    def autoslug(self):
        return slugify(self.user.username)

    @property
    def is_hosting(self):
        return self.owned_places.filter(available=True, deleted=False).count()

    @property
    def is_in_book(self):
        return self.owned_places.filter(available=True, deleted=False, in_book=True).count()

    @property
    def places_confirmed(self):
        return all(p.confirmed for p in self.owned_places.filter(deleted=False, in_book=True))

    @property
    def supervised_by(self):
        places = self.owned_places.filter(deleted=False)
        return [superv for p in places for superv in p.supervised_by]

    @property
    def is_supervisor(self):
        return any(self.supervisor_of)

    @property
    def supervisor_of(self, code=False):
        countries = (Country(g.name) for g in self.user.groups.all() if len(g.name) == 2)
        return countries if code else [c.name for c in countries]

    def is_supervisor_of(self, profile=None, countries=None):
        """Compare intersection between responsabilities and given countries."""
        if all([profile, countries]) or not any([profile, countries]):
            raise ImproperlyConfigured(_("Profile.is_supervisor_of() needs "
                "either a profile or a list of countries."))
        countries = countries if countries else []
        if not countries:
            countries = profile.owned_places.filter(
                available=True, deleted=False).values_list('country', flat=True)
        supervised = self.user.groups.values_list('name', flat=True)
        return any(set(supervised) & set(countries))

    def set_supervisor_of(self, country=None, remove=False):
        group = Group.objects.get(name=str(country))
        if remove:
            return self.user.groups.remove(group)
        return self.user.groups.add(group)

    def __str__(self):
        if self.full_name.strip():
            return self.full_name
        elif self.user:
            return self.user.username
        return '--'

    def __lt__(self, other):
        return self.last_name < other.last_name

    def repr(self):
        return "{} ({})".format(self.__str__(), getattr(self.birth_date, 'year', "?"))

    def display_phones(self):
        return ", ".join(phone.display() for phone in self.phones.all())

    def get_absolute_url(self):
        return reverse('profile_detail', kwargs={
            'pk': self.pk,
            'slug': getattr(self, 'slug', self.autoslug)})

    def get_edit_url(self):
        return reverse('profile_edit', kwargs={
            'pk': self.pk,
            'slug': getattr(self, 'slug', self.autoslug)})

    def get_admin_url(self):
        return reverse('admin:hosting_profile_change', args=(self.id,))

    def confirm_all_info(self, confirm=True):
        """Confirm (or unconfirm) all confirmable objects for a profile."""
        now = timezone.now() if confirm else None
        self.confirmed_on = now
        with transaction.atomic():
            self.owned_places.filter(deleted=False).update(confirmed_on=now)
            self.phones.filter(deleted=False).update(confirmed_on=now)
            self.website_set.filter(deleted=False).update(confirmed_on=now)
            self.save()


class Place(TrackingModel, TimeStampedModel):
    owner = models.ForeignKey('hosting.Profile', verbose_name=_("owner"),
        related_name="owned_places", on_delete=models.CASCADE)
    address = models.TextField(_("address"), blank=True,
        help_text=_("e.g.: Nieuwe Binnenweg 176"))
    city = models.CharField(_("city"), max_length=255, blank=True,
        help_text=_("Name in the official language, not in Esperanto (e.g.: Rotterdam)"),
        validators=[validate_not_all_caps, validate_not_too_many_caps])
    closest_city = models.CharField(_("closest big city"), max_length=255, blank=True,
        help_text=_("If you place is in a town near a bigger city. "
                    "Name in the official language, not in Esperanto."),
        validators=[validate_not_all_caps, validate_not_too_many_caps])
    postcode = models.CharField(_("postcode"), max_length=11, blank=True)
    state_province = models.CharField(_("State / Province"), max_length=70, blank=True)
    country = CountryField(_("country"))
    latitude = models.FloatField(_("latitude"), null=True, blank=True)
    longitude = models.FloatField(_("longitude"), null=True, blank=True)
    max_guest = models.PositiveSmallIntegerField(_("maximum number of guest"), blank=True, null=True)
    max_night = models.PositiveSmallIntegerField(_("maximum number of night"), blank=True, null=True)
    contact_before = models.PositiveSmallIntegerField(_("contact before"), blank=True, null=True,
        help_text=_("Number of days before people should contact host."))
    description = models.TextField(_("description"), blank=True,
        help_text=_("Description or remarks about your place."))
    short_description = models.CharField(_("short description"), max_length=140, blank=True,
        help_text=_("Used in the book and on profile, 140 characters maximum."))
    available = models.BooleanField(_("available"), default=True,
        help_text=_("If this place is searchable. If yes, you will be considered as host."))
    in_book = models.BooleanField(_("print in book"), default=True,
        help_text=_("If you want this place to be in the printed book. Must be available."))
    tour_guide = models.BooleanField(_("tour guide"), default=False,
        help_text=_("If you are ready to show your area to visitors."))
    have_a_drink = models.BooleanField(_("have a drink"), default=False,
        help_text=_("If you are ready to have a coffee or beer with visitors."))
    sporadic_presence = models.BooleanField(_("irregularly present"), default=False,
        help_text=_("If you are not often at this address and need an advance notification."))
    conditions = models.ManyToManyField('hosting.Condition', verbose_name=_("conditions"), blank=True)
    family_members = models.ManyToManyField('hosting.Profile', verbose_name=_("family members"), blank=True)
    authorized_users = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_("authorized users"), blank=True,
        help_text=_("List of users authorized to view most of data of this accommodation."))

    available_objects = AvailableManager()
    with_coord = WithCoordManager()

    class Meta:
        verbose_name = _("place")
        verbose_name_plural = _("places")
        default_manager_name = 'all_objects'

    @property
    def profile(self):
        """Proxy for self.owner. Rename 'owner' to 'profile' if/as possible."""
        return self.owner

    @property
    def bbox(self):
        """Return an OpenStreetMap formated bounding box.
        See http://wiki.osm.org/wiki/Bounding_Box
        """
        dx, dy = 0.007, 0.003  # Delta lng and delta lat around position
        lat, lng = self.latitude, self.longitude
        boundingbox = (lng - dx, lat - dy, lng + dx, lat + dy)
        return ",".join([str(coord) for coord in boundingbox])

    @property
    def any_accommodation_details(self):
        return any([self.description, self.contact_before, self.max_guest, self.max_night])

    @property
    def owner_available(self):
        return self.tour_guide or self.have_a_drink

    @property
    def supervised_by(self):
        group = Group.objects.get(name=self.country.code)
        return [user.profile for user in group.user_set.all()]

    def get_absolute_url(self):
        return reverse('place_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return ", ".join([self.city, force_text(self.country.name)]) if self.city else force_text(self.country.name)

    def display_family_members(self):
        family_members = self.family_members.exclude(pk=self.owner.pk).order_by('birth_date')
        return ", ".join(fm.repr() for fm in family_members)

    def display_conditions(self):
        return ", ".join(c.__str__() for c in self.conditions.all())


class Phone(TrackingModel, TimeStampedModel):
    PHONE_TYPE_CHOICES = PHONE_TYPE_CHOICES
    MOBILE, HOME, WORK, FAX = 'm', 'h', 'w', 'f'
    profile = models.ForeignKey('hosting.Profile', verbose_name=_("profile"),
        related_name="phones", on_delete=models.CASCADE)
    number = PhoneNumberField(_("number"),
        help_text=_("International number format begining with the plus sign (e.g.: +31 10 436 1044)"))
    country = CountryField(_("country"))
    comments = models.CharField(_("comments"), max_length=255, blank=True)
    type = models.CharField(_("phone type"), max_length=3,
        choices=PHONE_TYPE_CHOICES, default=MOBILE)

    class Meta:
        verbose_name = _("phone")
        verbose_name_plural = _("phones")
        unique_together = ('profile', 'number')

    @property
    def icon(self):
        if self.type == self.WORK:
            cls = "glyphicon-phone-alt"
        elif self.type == self.MOBILE:
            cls = "glyphicon-phone"
        elif self.type == self.FAX:
            cls = "glyphicon-print"
        else:  # self.HOME or ''
            cls = "glyphicon-earphone"
        title = self.get_type_display().capitalize()
        template = '<span class="glyphicon {cls}" title="{title}" data-toggle="tooltip" data-placement="left"></span>'
        return format_html(template, cls=cls, title=title)

    def __str__(self):
        """ as_e164             '+31104361044'
            as_international    '+31 10 436 1044'
            as_national         '010 436 1044'
            as_rfc3966          'tel:+31-10-436-1044'
        """
        return self.number.as_international

    def display(self):
        t = self.type or '(?)'
        return t + ': ' + self.number.as_international


class Website(TrackingModel, TimeStampedModel):
    profile = models.ForeignKey('hosting.Profile', verbose_name=_("profile"), on_delete=models.CASCADE)
    url = models.URLField(_("URL"))

    class Meta:
        verbose_name = _("website")
        verbose_name_plural = _("websites")

    def __str__(self):
        return self.url


class Condition(models.Model):
    """Hosting condition (e.g. bringing sleeping bag, no smoking...)."""
    name = models.CharField(_("name"), max_length=255,
        help_text=_("E.g.: 'Ne fumu'."))
    abbr = models.CharField(_("abbreviation"), max_length=20,
        help_text=_("Official abbreviation as used in the book. E.g.: 'Nef.'"))
    slug = models.SlugField(_("URL friendly name"))

    class Meta:
        verbose_name = _("condition")
        verbose_name_plural = _("conditions")

    def __str__(self):
        return self.name


class ContactPreference(models.Model):
    """Contact preference for a profile, whether by email, telephone or snail mail."""
    name = models.CharField(_("name"), max_length=255)

    class Meta:
        verbose_name = _("contact preference")
        verbose_name_plural = _("contact preferences")

    def __str__(self):
        return self.name
