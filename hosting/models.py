from datetime import date

from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.text import slugify
from django.db import models, transaction
from django.db.models import Q, F, Value as V
from django.db.models.functions import Concat, Substr
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from django_extensions.db.models import TimeStampedModel
from django.contrib.auth.models import Group
from phonenumber_field.modelfields import PhoneNumberField
from django_countries.fields import CountryField, Country

from .managers import (
    TrackingManager, NotDeletedManager, AvailableWithCoordManager, AvailableManager,
)
from .validators import (
    validate_not_all_caps, validate_not_too_many_caps, validate_no_digit, validate_latin,
    validate_not_in_future, TooFarPastValidator, TooNearPastValidator,
    validate_image, validate_size,
)
from .utils import UploadAndRenameAvatar, value_without_invalid_marker, format_lazy
from .gravatar import email_to_gravatar


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
    deleted_on = models.DateTimeField(_("deleted on"), default=None, blank=True, null=True)
    confirmed_on = models.DateTimeField(_("confirmed on"), default=None, blank=True, null=True)
    checked_on = models.DateTimeField(_("checked on"), default=None, blank=True, null=True)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("approved by"),
        blank=True, null=True,
        related_name="+", on_delete=models.SET_NULL)

    all_objects = TrackingManager()
    objects = NotDeletedManager()

    class Meta:
        abstract = True

    def set_check_status(self, set_by_user):
        if self.owner.user != set_by_user:
            self.checked_on, self.checked_by = timezone.now(), set_by_user
        else:
            self.checked_on, self.checked_by = None, None
        self.save()
        return self.checked_on, self.checked_by


class Profile(TrackingModel, TimeStampedModel):
    TITLE_CHOICES = TITLE_CHOICES

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(_("title"),
        blank=True,
        max_length=5, choices=TITLE_CHOICES)
    first_name = models.CharField(_("first name"),
        blank=True,
        max_length=255,
        validators=[validate_not_too_many_caps, validate_no_digit, validate_latin])
    last_name = models.CharField(_("last name"),
        blank=True,
        max_length=255,
        validators=[validate_not_too_many_caps, validate_no_digit, validate_latin])
    names_inversed = models.BooleanField(_("names in inverse order"),
        default=False)
    birth_date = models.DateField(_("birth date"),
        null=True, blank=True,
        validators=[TooFarPastValidator(200), validate_not_in_future],
        help_text=_("In the format year(4 digits)-month(2 digits)-day(2 digits)."))
    email = models.EmailField(_("public email"),
        blank=True,
        help_text=_("This email address will be used for the book. "
                    "Leave blank if you don't want this email to be public.\n"
                    "The system will never send emails to this address, "
                    "neither publish it on the site without your permission."))
    description = models.TextField(_("description"),
        blank=True,
        help_text=_("Short biography."))
    avatar = models.ImageField(_("avatar"),
        blank=True,
        upload_to=UploadAndRenameAvatar("avatars"),
        validators=[validate_image, validate_size],
        help_text=_("Small image under 100kB. Ideal size: 140x140 px."))
    contact_preferences = models.ManyToManyField('hosting.ContactPreference',
        blank=True, verbose_name=_("contact preferences"))

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    @property
    def owner(self):
        return self

    @property
    def full_name(self):
        if not self.names_inversed:
            combined_name = (self.first_name, self.last_name)
        else:
            combined_name = (self.last_name, self.first_name)
        real_name = " ".join(combined_name).strip()
        return real_name or (self.user.username.title() if self.user else " ")

    @property
    def name(self):
        return self.first_name or self.user.username.title()

    @property
    def anonymous_name(self):
        real_name = " ".join((self.first_name, self.last_name[:1] + "." if self.last_name else "")).strip()
        return real_name or (self.user.username.title() if self.user else " ")

    @property
    def age(self):
        return int((date.today() - self.birth_date).days / 365.24)

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            email = self.user.email if self.user else "family.member@pasportaservo.org"
            email = value_without_invalid_marker(email)
            return email_to_gravatar(email, settings.DEFAULT_AVATAR_URL)

    @property
    def icon(self):
        title = self.get_title_display().capitalize()
        template = '<span class="glyphicon glyphicon-user" title="{title}"></span>'
        return format_html(template, title=title)

    def get_fullname_display(self, quote='"', non_empty=False):
        template_first_name = '<span class={q}first-name{q}>{first}</span>'
        template_last_name = '<span class={q}last-name{q}>{last}</span>'
        template_username = '<span class={q}profile-noname{q}>{uname}</span>'
        if " ".join((self.first_name, self.last_name)).strip():
            if not self.names_inversed:
                template = (template_first_name, template_last_name)
            else:
                template = (template_last_name, template_first_name)
            return format_html(" ".join(template), q=mark_safe(quote), first=self.first_name, last=self.last_name)
        else:
            return format_html(template_username, q=mark_safe(quote),
                               uname=self.user.username.title() if self.user else ('--' if non_empty else " "))

    get_fullname_always_display = lambda self: self.get_fullname_display(non_empty=True)

    @property
    def autoslug(self):
        return slugify(self.user.username)

    @property
    def is_hosting(self):
        return self.owned_places.filter(available=True, deleted=False).count()

    @property
    def is_meeting(self):
        return sum((p.owner_available for p in self.owned_places.filter(deleted=False)), 0)

    @property
    def is_in_book(self):
        return self.owned_places.filter(
            #Q(confirmed=True) | Q(checked=True), #TODO: repair for shop
            available=True, deleted=False, in_book=True,
        ).count()

    @property
    def places_confirmed(self):
        return all(p.confirmed for p in self.owned_places.filter(deleted=False, in_book=True))

    def __str__(self):
        if self.full_name.strip():
            return self.full_name
        elif self.user:
            return self.user.username
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
            'slug': getattr(self, 'slug', self.autoslug) })

    def get_edit_url(self):
        return reverse('profile_edit', kwargs={
            'pk': self.pk,
            'slug': getattr(self, 'slug', self.autoslug) })

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

    @classmethod
    def mark_invalid_emails(cls, emails=None):
        models = {cls: None, get_user_model(): None}
        for model in models:
            models[model] = model.objects.filter(
                email__in=emails
            ).exclude(
                email__startswith=settings.INVALID_PREFIX
            ).update(
                email=Concat(V(settings.INVALID_PREFIX), F('email'))
            )
        return models

    @classmethod
    def mark_valid_emails(cls, emails=None):
        models = {cls: None, get_user_model(): None}
        for model in models:
            models[model] = model.objects.filter(
                email__in=emails,
                email__startswith=settings.INVALID_PREFIX
            ).update(
                email=Substr(F('email'), len(settings.INVALID_PREFIX) + 1)
            )
        return models


class Place(TrackingModel, TimeStampedModel):
    owner = models.ForeignKey('hosting.Profile', verbose_name=_("owner"),
        related_name="owned_places", on_delete=models.CASCADE)
    address = models.TextField(_("address"),
        blank=True,
        help_text=_("e.g.: Nieuwe Binnenweg 176"))
    city = models.CharField(_("city"),
        blank=True,
        max_length=255,
        validators=[validate_not_all_caps, validate_not_too_many_caps],
        help_text=_("Name in the official language, not in Esperanto (e.g.: Rotterdam)"))
    closest_city = models.CharField(_("closest big city"),
        blank=True,
        max_length=255,
        validators=[validate_not_all_caps, validate_not_too_many_caps],
        help_text=_("If your place is in a town near a bigger city. "
                    "Name in the official language, not in Esperanto."))
    postcode = models.CharField(_("postcode"),
        blank=True,
        max_length=11)
    state_province = models.CharField(_("State / Province"),
        blank=True,
        max_length=70)
    country = CountryField(_("country"))
    latitude = models.FloatField(_("latitude"),
        null=True, blank=True)
    longitude = models.FloatField(_("longitude"),
        null=True, blank=True)
    max_guest = models.PositiveSmallIntegerField(_("maximum number of guest"),
        null=True, blank=True)
    max_night = models.PositiveSmallIntegerField(_("maximum number of night"),
        null=True, blank=True)
    contact_before = models.PositiveSmallIntegerField(_("contact before"),
        null=True, blank=True,
        help_text=_("Number of days before people should contact host."))
    description = models.TextField(_("description"),
        blank=True,
        help_text=_("Description or remarks about your place."))
    short_description = models.CharField(_("short description"),
        blank=True,
        max_length=140,
        help_text=_("Used in the book and on profile, 140 characters maximum."))
    available = models.BooleanField(_("available"),
        default=True,
        help_text=_("If this place is searchable. If yes, you will be considered as host."))
    in_book = models.BooleanField(_("print in book"),
        default=True,
        help_text=_("If you want this place to be in the printed book. Must be available."))
    tour_guide = models.BooleanField(_("tour guide"),
        default=False,
        help_text=_("If you are ready to show your area to visitors."))
    have_a_drink = models.BooleanField(_("have a drink"),
        default=False,
        help_text=_("If you are ready to have a coffee or beer with visitors."))
    sporadic_presence = models.BooleanField(_("irregularly present"),
        default=False,
        help_text=_("If you are not often at this address and need an advance notification."))
    conditions = models.ManyToManyField('hosting.Condition', verbose_name=_("conditions"),
        blank=True)
    family_members = models.ManyToManyField('hosting.Profile', verbose_name=_("family members"),
        blank=True)
    blocked_from = models.DateField(_("unavailable from"),
        null=True, blank=True)
    blocked_until = models.DateField(_("unavailable until"),
        null=True, blank=True)
    authorized_users = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_("authorized users"),
        blank=True,
        help_text=_("List of users authorized to view most of data of this accommodation."))

    available_objects = AvailableManager()
    with_coord = AvailableWithCoordManager()

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
    def is_blocked(self):
        return any([self.blocked_until and self.blocked_until >= date.today(),
                    self.blocked_from and not self.blocked_until])

    def get_absolute_url(self):
        return reverse('place_detail', kwargs={'pk': self.pk})

    def get_locality_display(self):
        if self.city:
            return format_lazy("{city} ({state})", city=self.city, state=self.country.name)
        else:
            return self.country.name

    def __str__(self):
        return ", ".join([self.city, str(self.country.name)]) if self.city else str(self.country.name)

    def __repr__(self):
        return "<{} #{}: {}>".format(self.__class__.__name__, self.id, self.__str__())

    def rawdisplay_family_members(self):
        family_members = self.family_members.exclude(pk=self.owner.pk).order_by('birth_date')
        return ", ".join(fm.rawdisplay() for fm in family_members)

    def rawdisplay_conditions(self):
        return ", ".join(c.__str__() for c in self.conditions.all())

    def latexdisplay_conditions(self):
        return r"\, ".join(c.latex for c in self.conditions.all())


class Phone(TrackingModel, TimeStampedModel):
    PHONE_TYPE_CHOICES = PHONE_TYPE_CHOICES
    MOBILE, HOME, WORK, FAX = 'm', 'h', 'w', 'f'
    profile = models.ForeignKey('hosting.Profile', verbose_name=_("profile"),
        related_name="phones", on_delete=models.CASCADE)
    number = PhoneNumberField(_("number"),
        help_text=_("International number format begining with the plus sign (e.g.: +31 10 436 1044)"))
    country = CountryField(_("country"))
    comments = models.CharField(_("comments"),
        blank=True,
        max_length=255)
    type = models.CharField(_("phone type"),
        max_length=3,
        choices=PHONE_TYPE_CHOICES, default=MOBILE)

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
            cls = "glyphicon-earphone"
        elif self.type == self.MOBILE:
            cls = "glyphicon-phone"
        elif self.type == self.FAX:
            cls = "glyphicon-print"
        else:  # self.HOME or ''
            cls = "glyphicon-phone-alt"
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

    def __repr__(self):
        return "<{}: {}{} |p#{}>".format(self.__class__.__name__,
                                         "("+self.type+") " if self.type else "", self.__str__(),
                                         self.profile.id)

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
        return "<{}: {} |p#{}>".format(self.__class__.__name__, self.__str__(), self.profile.id)


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
