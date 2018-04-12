from datetime import timedelta

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    # Legal requirement of GDPR Article 8(1): [...] in relation to the offer
    # of information society services directly to a child, the processing of
    # the personal data of a child shall be lawful where the child is at least
    # 16 years old.
    USER_MIN_AGE = 16

    site_name = models.CharField(
        _("site name"),
        max_length=30, default='Pasporta Servo')

    google_analytics_key = models.CharField(
        max_length=13, default='UA-99737795-1', blank=True)

    salt = models.CharField(
        _("encryption salt"),
        max_length=30, default='salo',
        help_text=_("Salt used for encoded unique links. Change it to invalidate all links."))

    token_max_age = models.PositiveIntegerField(
        _("unique link lifetime"),
        default=3600 * 24 * 2,
        help_text=_("In seconds: 2 days = 3600 x 24 x 2 = 172800"))

    host_min_age = models.PositiveSmallIntegerField(
        _("minumum age for hosting"),
        default=17,
        validators=[MinValueValidator(USER_MIN_AGE)])

    meet_min_age = models.PositiveSmallIntegerField(
        _("minumum age for meeting"),
        default=16,
        validators=[MinValueValidator(USER_MIN_AGE)])

    confirmation_validity_period = models.DurationField(
        _("confirmation validity period"),
        default=timedelta(weeks=42),
        help_text=_("Delay (in days/hours) after which an object is no longer considered as confirmed."))

    def __str__(self):
        return str(_("Site Configuration"))

    class Meta:
        verbose_name = _("Site Configuration")
