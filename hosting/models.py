from __future__ import unicode_literals

from datetime import date

from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import format_html
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

import phonenumbers
from phonenumber_field.modelfields import PhoneNumberField
from django_extensions.db.models import TimeStampedModel
from django_countries.fields import CountryField

from .querysets import BaseQuerySet
from .validators import (
    validate_no_allcaps, validate_not_to_much_caps,
    validate_image, validate_size,
)
from .gravatar import email_to_gravatar


MRS, MR = 'Mrs', 'Mr'
TITLE_CHOICES = (
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


@python_2_unicode_compatible
class Profile(TimeStampedModel):
    TITLE_CHOICES = TITLE_CHOICES
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True)
    title = models.CharField(_("title"), max_length=5, choices=TITLE_CHOICES, blank=True)
    first_name = models.CharField(_("first name"), max_length=255, blank=True,
        validators=[validate_no_allcaps, validate_not_to_much_caps])
    last_name = models.CharField(_("last name"), max_length=255, blank=True,
        validators=[validate_no_allcaps, validate_not_to_much_caps])
    birth_date = models.DateField(_("birth date"), blank=True, null=True)
    description = models.TextField(_("description"), help_text=_("Short biography."), blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars", blank=True,
        validators=[validate_image, validate_size],
        help_text=_("Small image under 100kB. Ideal size: 140x140 px."))
    places = models.ManyToManyField('hosting.Place', verbose_name=_("places"),
        related_name='family_members', blank=True)
    contact_preferences = models.ManyToManyField('hosting.ContactPreference', verbose_name=_("contact preferences"), blank=True)

    checked = models.BooleanField(_("checked"), default=False)
    deleted = models.BooleanField(_("deleted"), default=False)

    objects = BaseQuerySet.as_manager()

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    @property
    def full_name(self):
        return " ".join((self.first_name, self.last_name))

    @property
    def anonymous_name(self):
        return " ".join((self.first_name, self.last_name[:1]))

    @property
    def age(self):
        return int((date.today() - self.birth_date).days / 365.24)

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            email = self.user.email if self.user else 'family.member@pasportaservo.org'
            return email_to_gravatar(email, settings.DEFAULT_AVATAR_URL)

    @property
    def icon(self):
        title=self.get_title_display().capitalize()
        template = '<span class="glyphicon glyphicon-user" title="{title}"></span>'
        return format_html(template, title=title)

    def __str__(self):
        username = self.user.username if self.user else '-'
        return self.full_name if self.full_name.strip() else username

    def get_admin_url(self):
        return reverse('admin:hosting_profile_change', args=(self.id,))


@python_2_unicode_compatible
class Place(TimeStampedModel):
    owner = models.ForeignKey('hosting.Profile', verbose_name=_("owner"), related_name="owned_places")
    address = models.TextField(_("address"), blank=True,
        help_text=_("e.g.: Nieuwe Binnenweg 176"))
    city = models.CharField(_("city"), max_length=255, blank=True,
        help_text=_("e.g.: Rotterdam"),
        validators = [validate_no_allcaps, validate_not_to_much_caps])
    closest_city = models.CharField(_("closest big city"), max_length=255, blank=True,
        help_text=_("If you place is in a town near a bigger city."),
        validators = [validate_no_allcaps, validate_not_to_much_caps])
    postcode = models.CharField(_("postcode"), max_length=11, blank=True)
    country = CountryField(_("country"))
    state_province = models.CharField(_("State / Province"), max_length=70, blank=True)
    latitude = models.FloatField(_("latitude"), null=True, blank=True)
    longitude = models.FloatField(_("longitude"), null=True, blank=True)
    max_guest = models.PositiveSmallIntegerField(_("maximum number of guest"), blank=True, null=True)
    max_night = models.PositiveSmallIntegerField(_("maximum number of night"), blank=True, null=True)
    contact_before = models.PositiveSmallIntegerField(_("contact before"), blank=True, null=True,
        help_text=_("Number of days before people should contact host."))
    description = models.TextField(_("description"), blank=True,
        help_text=_("Description or remarks about your place."))
    short_description = models.CharField(_("short description"), max_length=140, blank=True,
        help_text=_("Used in the book, 140 character maximum."))
    booked = models.BooleanField(_("booked"), default=False,
        help_text=_("If the place is currently booked."))
    available = models.BooleanField(_("available"), default=True,
        help_text=_("If this place is searchable. If yes, you will be considered as host."))
    in_book = models.BooleanField(_("print in book"), default=False,
        help_text=_("If you want this place to be in the printed book. Must be available."))
    tour_guide = models.BooleanField(_("tour guide"), default=False,
        help_text=_("If you are ready to show your area to visitors."))
    have_a_drink = models.BooleanField(_("have a drink"), default=False,
        help_text=_("If you are ready to have a coffee or beer with visitors."))
    conditions = models.ManyToManyField('hosting.Condition', verbose_name=_("conditions"), blank=True, null=True)
    authorized_users = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_("authorized users"), blank=True, null=True,
        help_text=_("List of users authorized to view most of data of this accommodation."))

    checked = models.BooleanField(_("checked"), default=False)
    deleted = models.BooleanField(_("deleted"), default=False)

    objects = BaseQuerySet.as_manager()

    class Meta:
        verbose_name = _("place")
        verbose_name_plural = _("places")

    @property
    def bbox(self):
        """Return an OpenStreetMap formated bounding box.
        See http://wiki.osm.org/wiki/Bounding_Box
        """
        dx, dy = 0.007, 0.003  # Delta lng and delta lat around position
        lat, lng = self.latitude, self.longitude
        boundingbox = (lng - dx, lat - dy, lng + dx, lat + dy)
        return ",".join([str(coord) for coord in boundingbox])

    def get_family_members(self):
        return [m.first_name +" ("+ str(m.age) +")" for m in self.family_members.all()]

    def __str__(self):
        return self.city


@python_2_unicode_compatible
class Phone(TimeStampedModel):
    PHONE_TYPE_CHOICES = PHONE_TYPE_CHOICES
    MOBILE, HOME, WORK, FAX = 'm', 'h', 'w', 'f'
    profile = models.ForeignKey('hosting.Profile', verbose_name=_("profile"), related_name="phones")
    number = PhoneNumberField(_("number"))
    country = CountryField(_("country"))
    comments = models.CharField(_("comments"), max_length=255, blank=True)
    type = models.CharField(_("phone type"), max_length=3,
        choices=PHONE_TYPE_CHOICES, default=MOBILE)

    checked = models.BooleanField(_("checked"), default=False)
    deleted = models.BooleanField(_("deleted"), default=False)

    objects = BaseQuerySet.as_manager()

    class Meta:
        verbose_name = _("phone")
        verbose_name_plural = _("phones")

    @property
    def icon(self):
        if self.type == self.HOME:
            cls = "glyphicon-earphone"
        elif self.type == self.WORK:
            cls = "glyphicon-phone-alt"
        elif self.type == self.MOBILE:
            cls = "glyphicon-phone"
        elif self.type == self.FAX:
            cls = "glyphicon-print"
        title=self.get_type_display().capitalize()
        template = '<span class="glyphicon {cls}" title="{title}"></span>'
        return format_html(template, cls=cls, title=title)

    def __str__(self):
        """ as_e164             '+31104361044'
            as_international    '+31 10 436 1044'
            as_national         '010 436 1044'
            as_rfc3966          'tel:+31-10-436-1044'
        """
        return self.number.as_international


@python_2_unicode_compatible
class Website(TimeStampedModel):
    profile = models.ForeignKey('hosting.Profile', verbose_name=_("profile"))
    url = models.URLField(_("URL"))

    checked = models.BooleanField(_("checked"), default=False)
    deleted = models.BooleanField(_("deleted"), default=False)

    objects = BaseQuerySet.as_manager()

    class Meta:
        verbose_name = _("website")
        verbose_name_plural = _("websites")

    def __str__(self):
        return self.url


@python_2_unicode_compatible
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


@python_2_unicode_compatible
class ContactPreference(models.Model):
    """Contact preference for a profile, whether by email, telephone or snail mail."""
    name = models.CharField(_("name"), max_length=255)

    class Meta:
        verbose_name = _("contact preference")
        verbose_name_plural = _("contact preferences")

    def __str__(self):
        return self.name
