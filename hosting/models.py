from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

import phonenumbers
from phonenumber_field.modelfields import PhoneNumberField
from django_extensions.db.models import TimeStampedModel
from django_countries.fields import CountryField

from .validators import validate_no_allcaps, validate_not_to_much_caps


MRS, MR = 'Mrs', 'Mr'
TITLE_CHOICES = (
    (MRS, _("Mrs")),
    (MR, _("Mr")),
)


MOBILE, HOME, WORK = 'm', 'h', 'w'
PHONE_TYPE_CHOICES = (
    (MOBILE, _("mobile")),
    (HOME, _("home")),
    (WORK, _("work")),
)


@python_2_unicode_compatible
class Profile(TimeStampedModel):
    TITLE_CHOICES = TITLE_CHOICES
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    title = models.CharField(_("title"), max_length=5, choices=TITLE_CHOICES)
    first_name = models.CharField(_("first name"), max_length=255, blank=True,
        validators = [validate_no_allcaps, validate_not_to_much_caps])
    last_name = models.CharField(_("last name"), max_length=255, blank=True,
        validators = [validate_no_allcaps, validate_not_to_much_caps])
    birth_date = models.DateField(_("birth date"), blank=True, null=True)
    description = models.TextField(_("description"), help_text=_("All about yourself."), blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars", blank=True)
    places = models.ManyToManyField('hosting.Place', verbose_name=_("places"), blank=True)
    phones = models.ManyToManyField('hosting.Phone', verbose_name=_("phone numbers"), blank=True)

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    @property
    def full_name(self):
        return " ".join((self.first_name, self.last_name))

    @property
    def anonymous_name(self):
        return " ".join((self.first_name, self.last_name[:1]))

    def __str__(self):
        return self.full_name if self.full_name else self.user.username


@python_2_unicode_compatible
class Place(TimeStampedModel):
    address = models.CharField(_("address"), max_length=255,
        help_text=_("e.g.: Nieuwe Binnenweg 176"))
    city = models.CharField(_("city"), max_length=255,
        help_text=_("e.g.: Rotterdam"),
        validators = [validate_no_allcaps, validate_not_to_much_caps])
    closest_city = models.CharField(_("closest big city"), max_length=255, blank=True,
        help_text=_("If you place is in a town near a bigger city."),
        validators = [validate_no_allcaps, validate_not_to_much_caps])
    postcode = models.CharField(_("postcode"), max_length=10)
    country = CountryField(_("country"))
    latitude = models.FloatField(_("latitude"), null=True, blank=True)
    longitude = models.FloatField(_("longitude"), null=True, blank=True)
    max_host = models.PositiveSmallIntegerField(_("maximum number of host"), blank=True, null=True)
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

    def __str__(self):
        return self.city


@python_2_unicode_compatible
class Phone(TimeStampedModel):
    PHONE_TYPE_CHOICES = PHONE_TYPE_CHOICES
    MOBILE, HOME, WORK = 'm', 'h', 'w'
    number = PhoneNumberField()
    type = models.CharField(_("phone type"), max_length=3,
        choices=PHONE_TYPE_CHOICES, default=MOBILE)

    class Meta:
        verbose_name = _("phone")
        verbose_name_plural = _("phones")

    def __str__(self):
        """ as_e164             '+31104361044'
            as_international    '+31 10 436 1044'
            as_national         '010 436 1044'
            as_rfc3966          'tel:+31-10-436-1044'
        """
        return self.number.as_international


@python_2_unicode_compatible
class Condition(TimeStampedModel):
    """Hosting condition (e.g. bringing sleeping bag, no smoking...)."""
    name = models.CharField(_("name"), max_length=255,
        help_text=_("E.g.: 'Ne fumu'."))
    abbr = models.CharField(_("name"), max_length=20,
        help_text=_("Official abbreviation as used in the book. E.g.: 'Nef.'"))
    slug = models.SlugField()
    

    class Meta:
        verbose_name = _("condition")
        verbose_name_plural = _("conditions")

    def __str__(self):
        return self.name
