from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

import phonenumbers

from django_extensions.db.models import TimeStampedModel
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

MRS, MR = 'Mrs', 'Mr'
TITLE_CHOICES = (
    (MRS, _("Mrs")),
    (MR, _("Mr")),

)

MOBILE, HOME, WORK = 'm', 'h', 'w'
PHONE_TYPE_CHOICES = (
    (MOBILE, _("Mobile")),
    (HOME, _("Home")),
    (WORK, _("Work")),
)

@python_2_unicode_compatible
class Profile(TimeStampedModel):
    TITLE_CHOICES = TITLE_CHOICES
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    title = models.CharField(_("title"), max_length=5, choices=TITLE_CHOICES)
    birth_date = models.DateField(_("birth date"), blank=True, null=True)
    places = models.ManyToManyField('hosting.Place', verbose_name=_("places"), blank=True)
    phones = models.ManyToManyField('hosting.Phone', verbose_name=_("phone numbers"), blank=True)

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    @property
    def anonymous_name(self):
        return " ".join((self.user.first_name, self.user.last_name[0]))

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username

@python_2_unicode_compatible
class Place(TimeStampedModel):
    address = models.CharField(_("address"), max_length=255)
    city = models.CharField(_("city"), max_length=255)
    postcode = models.CharField(_("postcode"), max_length=10)
    country = CountryField(_("country"))
    latitude = models.FloatField(_("latitude"), null=True, blank=True)
    longitude = models.FloatField(_("longitude"), null=True, blank=True)
    max_host = models.PositiveSmallIntegerField(_("maximum number of host"), blank=True, null=True)
    max_night = models.PositiveSmallIntegerField(_("maximum number of night"), blank=True, null=True)
    contact_before = models.PositiveSmallIntegerField(_("contact before"), blank=True, null=True,
        help_text=_("Number of days before people should contact host."))
    description = models.TextField(_("description"), blank=True)
    small_description = models.CharField(_("small description"), max_length=140, blank=True,
        help_text=_("Used in the book, 140 character maximum."))
    booked = models.BooleanField(_("booked"), default=False)
    available = models.BooleanField(_("available"), default=True)
    in_book = models.BooleanField(_("print in book"), default=False,
        help_text=_("If you want this place to be in the printed book"))
    conditions = models.ManyToManyField('hosting.Condition', verbose_name=_("conditions"), blank=True, null=True)

    class Meta:
        verbose_name = _("place")
        verbose_name_plural = _("places")

    @property
    def bbox(self):
        dx, dy = 0.007, 0.003  # Delta x and delta y around point
        lat, lng = self.latitude, self.longitude
        boundingbox = (lng - dx, lat - dy, lng + dx, lat + dy)
        return ",".join([str(coord) for coord in boundingbox])

    def __str__(self):
        return self.city

@python_2_unicode_compatible
class Phone(TimeStampedModel):
    PHONE_TYPE_CHOICES = PHONE_TYPE_CHOICES
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
    name = models.CharField(_("name"), max_length=255)

    class Meta:
        verbose_name = _("condition")
        verbose_name_plural = _("conditions")

    def __str__(self):
        return self.name
